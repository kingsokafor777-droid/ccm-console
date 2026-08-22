# ccm-console research basis

| Source | Architecture consequence |
|---|---|
| [NIST SP 800-137](https://csrc.nist.gov/pubs/sp/800/137/final) | The console exposes technical visibility and contextual response signals, not an automated authorization or assurance decision. |
| [NIST SP 800-37 Rev. 2](https://csrc.nist.gov/pubs/sp/800/37/r2/final) | Monitoring, assessment, authorization, responsibility, and accountability remain distinct organizational functions. |
| [OWASP API Security Top 10 2023](https://owasp.org/www-project-api-security/) | Every resource-by-ID route needs tenant/object authorization, and privileged workbench mutations require a distinct function-level role check. |
| [FastAPI security documentation](https://fastapi.tiangolo.com/tutorial/security/) | FastAPI security dependencies and OpenAPI schemes support an explicit bearer-token boundary; the application does not implement a general-purpose identity provider. |

> These references inform security and product boundaries. They do not turn ccm-console
> into a NIST implementation, an audit tool, or a compliance certification product.
