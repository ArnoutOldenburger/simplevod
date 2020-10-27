#! /usr/bin/perl

use strict;
use warnings;

use Digest::MD5;
use JSON;
use File::Basename;
use File::Copy;
use File::Temp;
use File::Spec;
use LWP::UserAgent;

my $ua = LWP::UserAgent->new;
$ua->env_proxy;

my $configfile = 'cfg/config.json';

die "Can't open configfile '$configfile'\n" if (!-e $configfile);

open my $fh, "<:unix", $configfile or die "Couldn't open $configfile: $!\n";
read $fh, my $config, -s $fh or die "Couldn't read $configfile: $!";
close $fh;

my $data = decode_json $config;

FEED:
for my $feed ( @{$data->{feeds}} ) {
  next FEED if $feed->{source} ne 'xml';
  next FEED if !$feed->{url};

  my ($fh, $tempfile) = File::Temp::tempfile();

  my $response = $ua->get(
    $feed->{url},
    ':content_file' => $tempfile,
  );
  if ($response->is_success) {

    # test if directory exists, create if not
    if ( !-d $feed->{dir} ) {
      mkdir $feed->{dir} || die "Can't create $feed->{dir}: $!\n";
    } 

    # test if existing metadatafile exists
    my $existingmetadatafile = 
      File::Spec->catfile(
        $feed->{dir},
        basename($feed->{url}, '.xml') . '.done');

    # if file exists, check if our remote file is different
    if ( -e $existingmetadatafile ) {
      my $existingdigest = getdigest($existingmetadatafile);
      my $newdigest = getdigest($tempfile);
      next FEED if $existingdigest eq $newdigest;
    }

    # copy new file in place
    move($tempfile, File::Spec->catfile($feed->{dir}, basename($feed->{url})));
  } else {
    warn "$feed->{url} gives " . $response->status_line . "\n";
  }
}

exit;

sub getdigest {
  my $filename = shift || die "need filename";
  if ( open my $fh, '<', $filename ) {
    binmode $fh;
    my $md5 = Digest::MD5->new();
    $md5->addfile($fh);
    close $fh;
    return $md5->hexdigest();
  }
  else {
    die "Cannot open $filename: $!\n";
  }
} 

