#!/usr/bin/perl
# Phase 4: JSON health endpoint and fixed-target read-only whitelist listing.

use strict;
use warnings;

use JSON::PP qw(encode_json);
use WebminCore;

sub send_json {
	my ($status, $payload) = @_;
	my %reason = (
		200 => 'OK',
		400 => 'Bad Request',
		403 => 'Forbidden',
		404 => 'Not Found',
		405 => 'Method Not Allowed',
		409 => 'Conflict',
		500 => 'Internal Server Error',
	);

	print 'Status: ' . $status . ' ' . ($reason{$status} || 'Error') . "\r\n";
	print "Content-Type: application/json; charset=UTF-8\r\n";
	print "Cache-Control: no-store\r\n";
	print "X-Content-Type-Options: nosniff\r\n\r\n";
	print encode_json($payload);
	exit;
}

sub send_error {
	my ($status, $code, $message) = @_;
	send_json($status, {
		success => JSON::PP::false,
		error   => {
			code    => $code,
			message => $message,
		},
	});
}

sub decode_query_component {
	my ($value) = @_;
	return undef if $value =~ /%(?![0-9A-Fa-f]{2})/;
	$value =~ tr/+/ /;
	$value =~ s/%([0-9A-Fa-f]{2})/chr(hex($1))/eg;
	return $value;
}

sub parse_parameters {
	my ($raw, $allowed) = @_;
	return ({}, undef) if $raw eq '';
	my %parameters;
	for my $pair (split(/&/, $raw, -1)) {
		my ($raw_name, $raw_value) = split(/=/, $pair, 2);
		$raw_value = '' if !defined $raw_value;
		my $name = decode_query_component($raw_name);
		my $value = decode_query_component($raw_value);
		return (undef, 'Malformed request parameters')
			if !defined($name) || !defined($value);
		return (undef, 'Unsupported request parameter')
			if !exists($allowed->{$name}) || exists $parameters{$name};
		$parameters{$name} = $value;
	}
	return (\%parameters, undef);
}

sub request_action {
	my ($parameters, $error) = parse_parameters($ENV{'QUERY_STRING'} || '', {
		action => 1,
	});
	return (undef, $error) if $error;
	return ($parameters->{'action'}, undef);
}

sub post_parameters {
	my $length = $ENV{'CONTENT_LENGTH'} || 0;
	return (undef, 'Invalid request body') if $length !~ /\A\d+\z/ || $length > 4096;
	return (undef, 'Unsupported request content type')
		if ($ENV{'CONTENT_TYPE'} || '') !~ /\Aapplication\/x-www-form-urlencoded(?:;|\z)/i;

	my $body = '';
	while (length($body) < $length) {
		my $read = read(STDIN, my $chunk, $length - length($body));
		return (undef, 'Unable to read request body') if !defined($read) || $read == 0;
		$body .= $chunk;
	}
	return parse_parameters($body, { address => 1 });
}


my $loaded = eval {
	&init_config();
	do './kmsfirewall-lib.pl' or die 'module library unavailable';
	do './auth-lib.pl' or die 'authorization library unavailable';
	1;
};
send_error(500, 'INTERNAL_ERROR', 'Internal server error') if !$loaded;

send_error(403, 'FORBIDDEN', 'KMS Firewall API access denied')
	if !api_authorized();

my ($action, $query_error) = request_action();
send_error(400, 'INVALID_PARAMETER', $query_error) if $query_error;

my $method = uc($ENV{'REQUEST_METHOD'} || 'GET');

send_error(405, 'METHOD_NOT_ALLOWED', 'HTTP method not allowed')
	if (!defined($action) || $action eq 'status') && $method ne 'GET';

send_json(200, {
	success => JSON::PP::true,
	module  => 'kmsfirewall',
	version => module_version(),
	status  => 'ok',
}) if !defined($action) || $action eq 'status';

if ($action eq 'list') {
	send_error(405, 'METHOD_NOT_ALLOWED', 'HTTP method not allowed') if $method ne 'GET';
	my ($addresses, $error) = read_kms_whitelist();
	send_error($error->{'http_status'}, $error->{'code'}, $error->{'message'})
		if $error;
	send_json(200, {
		success   => JSON::PP::true,
		module    => 'kmsfirewall',
		version   => module_version(),
		action    => 'list',
		addresses => $addresses,
	});
}

if ($action eq 'add') {
	send_error(405, 'METHOD_NOT_ALLOWED', 'HTTP method not allowed') if $method ne 'POST';
	my ($parameters, $parameter_error) = post_parameters();
	send_error(400, 'INVALID_PARAMETER', $parameter_error) if $parameter_error;
	send_error(400, 'INVALID_ADDRESS', 'Address is required')
		if !exists($parameters->{'address'}) || $parameters->{'address'} eq '';
	send_error(400, 'INVALID_ADDRESS', 'Invalid IPv4 address or CIDR')
		if !valid_ipv4_or_cidr($parameters->{'address'});
	my $address = normalize_ipv4_or_cidr($parameters->{'address'});

	my ($addresses, $error) = add_kms_whitelist($address);
	send_error($error->{'http_status'}, $error->{'code'}, $error->{'message'})
		if $error;
	send_json(200, {
		success   => JSON::PP::true,
		module    => 'kmsfirewall',
		version   => module_version(),
		action    => 'add',
		address   => $address,
		addresses => $addresses,
	});
}

send_error(405, 'METHOD_NOT_ALLOWED', 'HTTP method not allowed') if $method ne 'GET';

send_error(404, 'INVALID_ACTION', 'Unsupported API action');
