# Security

## Pre-alpha approval boundary

v0.4.1 binds explicitly verified, unexpired approval evidence to an exact proposal and gate, but
does not authenticate actors or verify signatures. Asserted evidence and the fake provider are not
production trust boundaries. Runtime predicates fail closed before provider work; observations
remain evidence and cannot rewrite authority.

This pre-alpha package performs offline declaration parsing; it is not a security boundary and makes no runtime assurance. Report vulnerabilities privately through GitHub's security advisory facility. Never include secrets. Provider execution, durable state, identity, PKI, routing, and federation are deferred.
