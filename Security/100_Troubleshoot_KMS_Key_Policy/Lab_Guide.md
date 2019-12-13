# Level 100: AWS Account and Root User: Lab Guide

## 1. Create 2 additional IAM users with the following policy

user-1
user-2

```
{
  "Statement": [
    {
      "Action": [
        "s3:*",
        "iam:List*"
      ],
      "Resource": "*",
      "Effect": "Allow"
    }
  ]
}
```

## 2. Create the Encryption Key

1. In the AWS Management Console, click on IAM.
2. Click Encryption keys from the left-hand menu.

3. Click Get Started Now.

4. Click Create key.

5. Under Alias (required), enter "mykey".

6. Select the checkbox next to your own logged in user/role.

7. Select the entire key policy and copy it to the clipboard.

Click Finish.

### 2. Configure the Encryption Key for Users

* Click mykey.

* Under Key Users, click Add.

Select the checkbox next to user-1.

Click Attach.

On the Key Policy row, click the Switch to policy view link.

Select the permissions for user-1 and copy them.

Paste a copy to the end of permissions.

### 3. Create a Bucket Using the Key and Upload an Object

Select Services from the top menu bar.

Select S3.

Click + Create bucket

Under Bucket name enter "mybucket" with several random numbers afterward to ensure uniqueness.

Select Default encryption.

Select AWS-KMS.

From the dropdown, select mykey.

Click Create bucket.

Click on the bucket name.

Click the Upload button.

Click Add files and select any file from your local drive.

Select a file to upload.

### 4. Test the Policy

Log out of the AWS Console.

Log back into AWS using the user-1 credentials you created

Click S3.

Click the bucket name.

Click the uploaded file.

Click the Download button and verify the download works.

Log out of the AWS Console.

Log back into AWS using the user-2 credentials you created

Click S3.

Click the bucket name.

Click the uploaded file.

Click the Download button and verify you receive an access denied message.

### 5. Conclusion

Congratulations — you've completed this hands-on lab!
