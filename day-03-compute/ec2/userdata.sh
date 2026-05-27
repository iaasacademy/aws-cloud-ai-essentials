#!/bin/bash

# Update OS packages
dnf update -y

# Install Apache and AWS CLI
dnf install -y httpd aws-cli

# Enable Apache to start on boot
systemctl enable httpd

# Clear default web root content
rm -rf /var/www/html/*

# Copy all files from S3 bucket to Apache web root
aws s3 sync s3://"your-bucket-name-here" /var/www/html

# Set ownership and permissions
chown -R apache:apache /var/www/html
chmod -R 755 /var/www/html

# Start Apache
systemctl start httpd