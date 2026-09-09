#!/usr/bin/perl
# Phase 1: status-only module landing page. No firewall commands are run.

use strict;
use warnings;

use WebminCore;
&init_config();
do './kmsfirewall-lib.pl' or &error("Failed to load module library");

print &header($text{'index_title'}, '', '');

print &ui_table_start($text{'status_title'}, 'width=100%', 2);
print &ui_table_row($text{'status_module'}, 'kmsfirewall');
print &ui_table_row($text{'status_version'}, &module_version());
print &ui_table_row($text{'status_api'},
	&api_is_enabled() ? $text{'status_enabled'} : $text{'status_disabled'});
print &ui_table_row($text{'status_nft'},
	&command_exists('nft') ? $text{'status_available'} : $text{'status_not_found'});
print &ui_table_row($text{'status_target'},
	'inet ' . &configured_table() . ' / ' . &configured_set());
print &ui_table_end();

print '<p>' . &text('index_phase1') . '</p>\n';
print &footer('', $text{'index_return'});
