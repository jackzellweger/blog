---
title: How to create and edit sops files
date: 2025-04-16
---
# How to create and edit sops files
### How to create a sops file w/ secrets
1. Make sure you have Local Dev up and running on your machine.
2. Determine which environment the secret is for.
3. Use the AWS command line utility with the correct profile to log into that environment. For example, if you're creating a secret for `prod` with the superuser account, you want to use `aws sso login --profile <PROF>`. If you're creating a secret for `uat` with the superuser account, you want to use `aws sso login --profile <PROF>`.
4. Navigate to the proper environment's folder. For example, if it's a secret for `prod`, navigate to `<PROD DIR>`. If it's a secret for UAT, navigate to `<UAT DIR>`.
5. Once you're in the directory, run the command `sops <YOUR_FILE_NAME_HERE>.yaml`. Don't forget the `.yaml` at the end of your file.
6. You will enter a `vim` editor. Add your details with proper YAML syntax.
### How to access a sops file
1. Log into the correct AWS account using the AWS command line utility. For example, when logging into production with the superuser profile, the command looks like this:  `aws sso login --profile <PROF>`. When logging into UAT with the superuser profile, the command looks like this `aws sso login --profile <PROF>`.
2. Run the following command to decrypt the file `sops /path/to/file.yaml`
3. If you get an error, you've probably logged in with the wrong profile, or don't have proper permissions to view this file.
4. Once you've decrypted the file, you will enter a `vim` editor. Edit and be sure to maintain proper YAML syntax.
