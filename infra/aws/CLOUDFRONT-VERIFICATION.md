# CloudFront account verification — deployment lesson

The first deployment was refused with:

> Your account must be verified before you can add new CloudFront resources.

This was an AWS account/service restriction rather than a missing deployment-policy permission. CloudFormation rolled back the dedicated bucket and origin access control. Their DELETE_COMPLETE states and the stack's ROLLBACK_COMPLETE state were verified before removing the empty failed-stack record.

The account owner requested verification through AWS account/billing support. AWS confirmed verification while retaining the existing Free plan and credits. The retry succeeded under the same scoped non-root deployment identity. No broader IAM policy or support-plan upgrade was needed.

For a similar error in your own account, contact [AWS Support](https://console.aws.amazon.com/support/home#/) with your error and request ID. Complete any ownership checks directly with AWS. Do not add passwords, MFA codes, billing documents, or private correspondence to this repository.

The successful release is documented in [deployment evidence](../../docs/notes/deployed-portfolio.md).
