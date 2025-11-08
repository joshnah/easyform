# Configuration variables - modify these as needed
$CertificateName = "easyform"
$CertificatePassword = "MyPassword123"
$OutputDirectory = "$env:USERPROFILE\Desktop"
$MSIXPath = "$env:USERPROFILE\Desktop\codes\easyform\EasyForm.msix"

# Create a new self-signed certificate for code signing
# This certificate will be used to sign the MSIX package
$cert = New-SelfSignedCertificate `
  -Type CodeSigningCert `
  -Subject "CN=$CertificateName" `
  -CertStoreLocation "Cert:\CurrentUser\My"

# Export the public certificate (.cer file) to the specified directory
# This file contains only the public key and can be shared
Export-Certificate -Cert $cert -FilePath "$OutputDirectory\$CertificateName.cer"

# Export the private certificate (.pfx file) with password protection
# This file contains both public and private keys and should be kept secure
Export-PfxCertificate -Cert $cert -FilePath "$OutputDirectory\$CertificateName.pfx" -Password (ConvertTo-SecureString -String $CertificatePassword -Force -AsPlainText)

# Import the PFX certificate to the TrustedPeople store for the current user
# This allows the current user to trust applications signed with this certificate
Import-PfxCertificate -FilePath "$OutputDirectory\$CertificateName.pfx" -CertStoreLocation Cert:\CurrentUser\TrustedPeople -Password (ConvertTo-SecureString -String $CertificatePassword -Force -AsPlainText)  

# Set the path to the public certificate file
$certPath = "$OutputDirectory\$CertificateName.cer"

# Open the Trusted Root Certification Authorities store for the local machine
# This requires administrator privileges
$store = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root","LocalMachine")
$store.Open("ReadWrite")

# Load the certificate from file and add it to the trusted root store
# This makes the certificate trusted system-wide for all users
$cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($certPath)
$store.Add($cert)
$store.Close()

Write-Host "Certificate installed to Trusted Root Certification Authorities successfully."

# Sign the MSIX package using signtool
# /fd SHA256: Use SHA256 hash algorithm
# /a: Automatically select the best signing certificate
# /f: Specify the PFX file path
# /p: Provide the password for the PFX file
signtool sign /fd SHA256 /a /f "$OutputDirectory\$CertificateName.pfx" /p $CertificatePassword $MSIXPath

# Install the signed MSIX package
# -ForceApplicationShutdown: Close the app if it's running
# -ForceUpdateFromAnyVersion: Allow downgrade or reinstallation
Add-AppxPackage -ForceApplicationShutdown -ForceUpdateFromAnyVersion $MSIXPath