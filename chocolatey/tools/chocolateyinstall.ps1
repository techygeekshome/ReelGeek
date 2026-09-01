$ErrorActionPreference = 'Stop'

# ReelGeek ships an Inno Setup installer. The package downloads it from the GitHub release for the
# matching tag and verifies it against a SHA-256 checksum rather than embedding the binary. Because
# nothing is embedded, this package must NOT contain a tools\VERIFICATION.txt - that file is only
# for packages that ship a binary inside the nupkg, and including one is what the USP 8.0.0
# submission was rejected for.
$packageArgs = @{
  packageName    = 'reelgeek'
  fileType       = 'exe'
  url            = 'https://github.com/techygeekshome/ReelGeek/releases/download/v1.0.0/ReelGeekSetup.exe'
  checksum       = 'a99878dd0bba01649807aaa1d2b9206dd31eb64c8ea6c98c4b49716ca6d95969'
  checksumType   = 'sha256'
  silentArgs     = '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-'
  validExitCodes = @(0, 3010, 1641)
}

Install-ChocolateyPackage @packageArgs
