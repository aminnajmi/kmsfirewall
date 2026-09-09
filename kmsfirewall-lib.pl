# Shared helpers for the KMS Firewall Webmin module.

use strict;
use warnings;

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

1;
