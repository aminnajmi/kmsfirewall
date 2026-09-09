# Authentication and authorization helpers for the KMS Firewall API.
# Webmin authenticates the HTTP request before this library is loaded.

use strict;
use warnings;

our ($remote_user, %config);

sub get_authenticated_user {
	return undef if !defined($remote_user) || $remote_user eq '';
	return $remote_user;
}

sub configured_api_user {
	my $user = $config{'api_authorized_user'} || 'kms-api';
	return undef if $user !~ /\A[A-Za-z0-9_.-]+\z/;
	return $user;
}

sub api_authorized {
	my $user = get_authenticated_user();
	my $configured_user = configured_api_user();
	return 0 if !defined($user) || !defined($configured_user);
	return 0 if $user ne $configured_user;

	# init_config enforces first-level module access. This is the module's
	# second-level ACL switch for the API endpoint.
	my %access = &get_module_acl();
	return 0 if defined($access{'api_access'}) && !$access{'api_access'};
	return 1;
}

1;
