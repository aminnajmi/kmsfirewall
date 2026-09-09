#!/usr/bin/perl
# Detailed ACL control for the API endpoint.

use strict;
use warnings;

our %text;

sub acl_security_form {
	my ($access) = @_;
	print &ui_table_row($text{'acl_api_access'},
		&ui_yesno_radio('api_access', $access->{'api_access'}));
}

sub acl_security_save {
	my ($access, $in) = @_;
	$access->{'api_access'} = $in->{'api_access'} eq '1' ? 1 : 0;
}

1;
