# Portfolio cost assumptions

The public release uses a private S3 origin and a CloudFront HTTPS distribution. No EC2, NAT Gateway, RDS, WAF, custom domain, paid model inference, or backend hosting is included.

Planning assumptions: artifact under 2 MB; about 1,000 visits/month, 20 requests/visit, and 2 GB data transfer. These are planning inputs, not measured traffic.

At the rates reviewed for the initial release, available CloudFront free allowances could cover this traffic. A $0.05 S3 planning allowance and roughly $0.25/month planning total without the assumed CloudFront allowance were used for a small demonstration. These figures are estimates, not quotes or guarantees. Other account usage, viewer geography, request volume, tax, eligibility, and pricing changes can alter the result. Check [CloudFront pricing](https://aws.amazon.com/cloudfront/pricing/pay-as-you-go/) and [S3 pricing](https://aws.amazon.com/s3/pricing/) before deployment.

The account owner authorized using existing credits for this static release only. Account balances, financial records, and support correspondence are intentionally excluded from the public repository. No account or support-plan upgrade was performed.

The script refuses a paid account plan and requires FREE/ACTIVE with at least $5 remaining USD credits. It also checks for an account-wide monthly budget at $5 or less, excluding credits, and a configured actual-spend email subscriber. Verify the email in the AWS console separately. Existing account usage can already exceed a budget threshold. Budgets are delayed alerts, not a hard spending cap; traffic is not capped by this deployment.

Credit or Free-plan expiry can interrupt the demo. The project configures no automatic plan upgrade. Review usage in AWS Billing and follow DEPLOYMENT.md to remove only the portfolio resources when the demo is no longer needed.
