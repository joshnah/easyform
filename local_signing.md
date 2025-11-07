$cert = New-SelfSignedCertificate `
  -Type CodeSigningCert `
  -Subject "CN=easyform" `
  -CertStoreLocation "Cert:\CurrentUser\My"

Export-Certificate -Cert $cert -FilePath "$env:USERPROFILE\Desktop\easyform.cer"
Export-PfxCertificate -Cert $cert -FilePath "$env:USERPROFILE\Desktop\easyform.pfx" -Password (ConvertTo-SecureString -String "MyPassword123" -Force -AsPlainText)


Import-PfxCertificate -FilePath "C:\Users\qc_de\Desktop\easyform.pfx" -CertStoreLocation Cert:\CurrentUser\TrustedPeople -Password (ConvertTo-SecureString -String "MyPassword123" -Force -AsPlainText)  


# Path to your .cer file
$certPath = "C:\Users\qc_de\Desktop\easyform.cer"

# Open the Trusted Root store for LocalMachine
$store = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root","LocalMachine")
$store.Open("ReadWrite")

# Load the certificate and add it
$cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($certPath)
$store.Add($cert)
$store.Close()

Write-Host "Certificate installed to Trusted Root Certification Authorities successfully."


signtool sign /fd SHA256 /a /f "$env:USERPROFILE\Desktop\easyform.pfx" /p MyPassword123 "C:\Users\qc_de\Desktop\codes\easyform\EasyForm.msix"

Add-AppxPackage -ForceApplicationShutdown -ForceUpdateFromAnyVersion "C:\Users\qc_de\Desktop\codes\easyform\EasyForm.msix"