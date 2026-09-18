# Antigravity Persistent Workspace Rule: FX SkillHub

You are working on FX SkillHub for Francis Xavier Engineering College (FXEC).

Always:
- inspect existing code before changing it
- preserve working behavior
- use official FXEC sources for institutional facts
- use real database records rather than hardcoded UI arrays
- attach provenance to institution-specific content
- never fabricate student/course/placement statistics
- never expose secrets
- validate all role permissions server-side
- write tests for security-sensitive changes
- verify critical flows in the browser
- report actual errors instead of hiding them
- do not remove tests just to make builds pass
- do not weaken security controls to make a demo pass
- use accessible UI patterns
- keep assessment timing server-authoritative
- treat camera/screen controls as browser-permission-based signals
- never claim 100% anti-cheat
- never let AI alone decide misconduct
- never issue a certificate without a verified completion event
- never duplicate certificate issuance
- keep a source registry for published institutional facts

When a request would introduce fake/static data, refuse that part and instead:
1. query the available authoritative source,
2. create an admin-input field, or
3. show an empty/pending state.

Before marking a task complete:
1. run tests,
2. run the relevant browser path,
3. inspect console/network errors,
4. summarize files changed,
5. list any residual risks.
