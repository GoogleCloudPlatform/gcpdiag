Create terraform project

```
terraform plan -var="billing_account_id=0123456-ABCDEF-987654" -var="org_id=123456789012"
terraform apply -var="billing_account_id=0123456-ABCDEF-987654" -var="org_id=123456789012"
```

Refresh json dumps:
```
make all
```
