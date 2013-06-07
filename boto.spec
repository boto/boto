Summary: Sirca boto
Name: sirca-boto
Version: 1.0.0
Group: Sirca/Boto
Vendor: SIRCA Ltd
License: Proprietary
Source0: %source
URL: %url
Release: %revision
BuildArch: noarch

Requires: python >= 2.6.6

%description
This package contains the Sirca boto, from commit %commit


# Prepare the build.  Nothing to do.
%prep
echo "Preparing"

%setup

%clean
echo "Cleaning"

# Compile everything
%build
rm -rf $RPM_BUILD_ROOT
echo "Building"
# Nothing to build as this is a python programA

%install
# Simple copy as this is a python program
echo "Installing"
ls
pwd
mkdir -p $RPM_BUILD_ROOT/%{python_sitelib}/%source_dir_name
cp -r %source_dir_name/boto/* $RPM_BUILD_ROOT/%{python_sitelib}/%source_dir_name

# Install applications
mkdir -p $RPM_BUILD_ROOT/usr/bin

%post

%files
%defattr(-,root,root)
%{python_sitelib}/%source_dir_name
