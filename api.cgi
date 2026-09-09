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

sub request_action {
	my $query = $ENV{'QUERY_STRING'} || '';
	return (undef, undef) if $query eq '';

	my %parameters;
	for my $pair (split(/&/, $query, -1)) {
		my ($raw_name, $raw_value) = split(/=/, $pair, 2);
		$raw_value = '' if !defined $raw_value;
		my $name = decode_query_component($raw_name);
		my $value = decode_query_component($raw_value);
		return (undef, 'Malformed query string')
			if !defined($name) || !defined($value);
		return (undef, 'Unsupported query parameter')
			if $name ne 'action' || exists $parameters{$name};
		$parameters{$name} = $value;
	}

	return ($parameters{'action'}, undef);
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

my $method = uc($ENV{'REQUEST_METHOD'} || 'GET');
send_error(405, 'METHOD_NOT_ALLOWED', 'HTTP method not allowed')
	if $method ne 'GET';

my ($action, $query_error) = request_action();
send_error(400, 'INVALID_PARAMETER', $query_error) if $query_error;

send_json(200, {
	success => JSON::PP::true,
	module  => 'kmsfirewall',
	version => module_version(),
	status  => 'ok',
}) if !defined($action) || $action eq 'status';

if ($action eq 'list') {
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

send_error(404, 'INVALID_ACTION', 'Unsupported API action');
