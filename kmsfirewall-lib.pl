# Shared helpers for the KMS Firewall Webmin module.

use strict;
use warnings;

use JSON::PP qw(decode_json);

do 'web-lib.pl';

our (%config, %text);

sub module_version {
	return '1.0';
}

sub configured_table {
	return $config{'nft_table'} || 'KMS-Firewall';
}

sub configured_set {
	return $config{'nft_set'} || 'kms_whitelist';
}

sub api_is_enabled {
	return ($config{'api_enabled'} // '1') eq '1' ? 1 : 0;
}

sub command_exists {
	my ($command) = @_;
	return 0 if !$command || $command !~ /\A[A-Za-z0-9_.-]+\z/;
	return scalar grep { -x $_ } map { "$_/$command" } split(/:/, $ENV{'PATH'} || '');
}

sub nft_command_path {
	# Only trusted, fixed locations are considered. No path is configurable by
	# an API request or module setting.
	for my $path ('/usr/sbin/nft', '/usr/bin/nft', '/sbin/nft', '/bin/nft') {
		return $path if -f $path && -x $path;
	}
	return undef;
}

sub valid_ipv4_or_cidr {
	my ($value) = @_;
	return 0 if !defined($value);
	my ($address, $prefix) = split(/\//, $value, 2);
	return 0 if defined($prefix) && $prefix !~ /\A(?:[0-9]|[12][0-9]|3[0-2])\z/;
	my @octets = split(/\./, $address, -1);
	return 0 if @octets != 4;
	for my $octet (@octets) {
		return 0 if $octet !~ /\A(?:0|[1-9][0-9]{0,2})\z/ || $octet > 255;
	}
	return 1;
}

sub normalize_ipv4_or_cidr {
	my ($value) = @_;
	return undef if !valid_ipv4_or_cidr($value);
	my ($address, $prefix) = split(/\//, $value, 2);
	return $address if !defined($prefix) || $prefix == 32;

	my $remaining = $prefix;
	my @normalized = map {
		my $bits = $remaining >= 8 ? 8 : $remaining;
		my $mask = $bits == 0 ? 0 : (0xFF << (8 - $bits)) & 0xFF;
		$remaining -= $bits;
		$_ & $mask;
	} split(/\./, $address);
	return join('.', @normalized) . '/' . $prefix;
}

sub valid_kms_target {
	my $table = configured_table();
	my $set = configured_set();
	return $table eq 'KMS-Firewall' && $set eq 'kms_whitelist'
		&& $table =~ /\A[A-Za-z0-9_.-]+\z/ && $set =~ /\A[A-Za-z0-9_.-]+\z/;
}

sub read_kms_whitelist {
	return (undef, {
		code => 'INVALID_INTERNAL_CONFIGURATION',
		message => 'Firewall target configuration is invalid',
		http_status => 500,
	}) if !valid_kms_target();

	my $nft = nft_command_path();
	return (undef, {
		code => 'NFT_NOT_FOUND',
		message => 'nftables command is not available',
		http_status => 500,
	}) if !defined($nft);

	my @command = ($nft, '-j', 'list', 'set', 'inet', 'KMS-Firewall', 'kms_whitelist');
	open(my $nft_output, '-|', @command) or return (undef, {
		code => 'NFTABLES_ERROR',
		message => 'Unable to execute nftables command',
		http_status => 500,
	});

	my $output = '';
	my $limit = 1024 * 1024;
	while (1) {
		my $chunk = '';
		my $read = read($nft_output, $chunk, 8192);
		last if defined($read) && $read == 0;
		return (undef, {
			code => 'NFTABLES_ERROR',
			message => 'Unable to read nftables output',
			http_status => 500,
		}) if !defined($read);
		$output .= $chunk;
		if (length($output) > $limit) {
			close($nft_output);
			return (undef, {
				code => 'NFT_OUTPUT_INVALID',
				message => 'Unexpected nftables output',
				http_status => 500,
			});
		}
	}
	my $closed = close($nft_output);
	return (undef, {
		code => 'NFTABLES_ERROR',
		message => 'nftables command failed',
		http_status => 500,
	}) if !$closed || $? != 0;
	return (undef, {
		code => 'NFT_OUTPUT_INVALID',
		message => 'Unexpected nftables output',
		http_status => 500,
	}) if $output !~ /\S/;

	my $decoded = eval { decode_json($output) };
	return (undef, {
		code => 'NFT_OUTPUT_INVALID',
		message => 'Unexpected nftables output',
		http_status => 500,
	}) if $@ || ref($decoded) ne 'HASH' || ref($decoded->{'nftables'}) ne 'ARRAY';

	my @sets = map { $_->{'set'} }
		grep {
			ref($_) eq 'HASH' && ref($_->{'set'}) eq 'HASH'
			&& defined($_->{'set'}->{'family'}) && $_->{'set'}->{'family'} eq 'inet'
			&& defined($_->{'set'}->{'table'}) && $_->{'set'}->{'table'} eq 'KMS-Firewall'
			&& defined($_->{'set'}->{'name'}) && $_->{'set'}->{'name'} eq 'kms_whitelist'
		} @{$decoded->{'nftables'}};
	return (undef, {
		code => 'NFT_OUTPUT_INVALID',
		message => 'Unexpected nftables output',
		http_status => 500,
	}) if @sets != 1 || !defined($sets[0]->{'type'}) || $sets[0]->{'type'} ne 'ipv4_addr'
		|| (exists($sets[0]->{'elem'}) && ref($sets[0]->{'elem'}) ne 'ARRAY');

	my $elements = $sets[0]->{'elem'} || [];
	my @addresses;
	for my $element (@{$elements}) {
		my $value;
		if (!ref($element)) {
			$value = $element;
		}
		elsif (ref($element) eq 'HASH'
			&& ref($element->{'prefix'}) eq 'HASH'
			&& defined($element->{'prefix'}->{'addr'}) && !ref($element->{'prefix'}->{'addr'})
			&& defined($element->{'prefix'}->{'len'})) {
			my $prefix = $element->{'prefix'};
			return (undef, {
				code => 'NFT_OUTPUT_INVALID',
				message => 'Unexpected nftables output',
				http_status => 500,
			}) if $prefix->{'len'} !~ /\A(?:[0-9]|[12][0-9]|3[0-2])\z/;
			$value = $prefix->{'addr'} . '/' . $prefix->{'len'};
		}
		else {
			return (undef, {
				code => 'NFT_OUTPUT_INVALID',
				message => 'Unexpected nftables output',
				http_status => 500,
			});
		}
		return (undef, {
			code => 'NFT_OUTPUT_INVALID',
			message => 'Unexpected nftables output',
			http_status => 500,
		}) if !valid_ipv4_or_cidr($value);
		push(@addresses, $value);
	}

	return (\@addresses, undef);
}

sub add_kms_whitelist {
	my ($address) = @_;
	$address = normalize_ipv4_or_cidr($address);
	return (undef, {
		code => 'INVALID_ADDRESS',
		message => 'Invalid IPv4 address or CIDR',
		http_status => 400,
	}) if !defined($address);

	my ($existing, $read_error) = read_kms_whitelist();
	return (undef, $read_error) if $read_error;
	return (undef, {
		code => 'ALREADY_EXISTS',
		message => 'Address already exists',
		http_status => 409,
	}) if grep { $_ eq $address } @{$existing};

	return (undef, {
		code => 'INVALID_INTERNAL_CONFIGURATION',
		message => 'Firewall target configuration is invalid',
		http_status => 500,
	}) if !valid_kms_target();
	my $nft = nft_command_path();
	return (undef, {
		code => 'NFT_NOT_FOUND',
		message => 'nftables command is not available',
		http_status => 500,
	}) if !defined($nft);

	my @command = ($nft, 'add', 'element', 'inet', 'KMS-Firewall',
		'kms_whitelist', '{', $address, '}');
	open(my $nft_output, '-|', @command) or return (undef, {
		code => 'NFT_COMMAND_FAILED',
		message => 'Unable to execute nftables command',
		http_status => 500,
	});
	while (1) {
		my $read = read($nft_output, my $chunk, 8192);
		last if defined($read) && $read == 0;
		return (undef, {
			code => 'NFT_COMMAND_FAILED',
			message => 'Unable to execute nftables command',
			http_status => 500,
		}) if !defined($read);
	}
	my $closed = close($nft_output);
	return (undef, {
		code => 'NFT_COMMAND_FAILED',
		message => 'nftables command failed',
		http_status => 500,
	}) if !$closed || $? != 0;

	my ($updated, $verify_error) = read_kms_whitelist();
	return (undef, {
		code => 'NFT_VERIFICATION_FAILED',
		message => 'Unable to verify whitelist update',
		http_status => 500,
	}) if $verify_error || !grep { $_ eq $address } @{$updated};
	return ($updated, undef);
}

1;
