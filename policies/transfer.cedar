// Agentic Zero Trust: authorization policy for the `transfer` action.
// Cedar semantics: default deny; any matching `forbid` overrides every `permit`.
// Amounts are integer cents. 1_000_000 = 10,000.00 (approval threshold); 10_000_000 = 100,000.00 (hard cap).

@id("permit-small-transfer")
permit (principal, action == Action::"transfer", resource)
when {
  principal.scopes.contains("transfer:create") &&
  context.amount_cents <= 1000000
};

@id("permit-approved-transfer")
permit (principal, action == Action::"transfer", resource)
when {
  principal.scopes.contains("transfer:create") &&
  context.amount_cents > 1000000 &&
  context.approval_valid
};

@id("forbid-unverified-beneficiary")
forbid (principal, action == Action::"transfer", resource)
unless { resource.registry_verified };

@id("forbid-sanctioned")
forbid (principal, action == Action::"transfer", resource)
when { resource.sanctioned };

@id("forbid-beneficiary-not-in-task")
forbid (principal, action == Action::"transfer", resource)
unless { resource.iban == context.task_beneficiary };

// The task cap is a cumulative budget: what this token already moved counts against it
// (blocks replaying the token or splitting one large payment into several small ones).
@id("forbid-over-task-cap")
forbid (principal, action == Action::"transfer", resource)
when { context.amount_cents + context.task_spent_cents > context.task_max_cents };

@id("forbid-source-not-in-task")
forbid (principal, action == Action::"transfer", resource)
unless { context.source == context.task_source };

@id("forbid-currency-not-in-task")
forbid (principal, action == Action::"transfer", resource)
unless { context.currency == context.task_currency };

@id("forbid-hard-cap")
forbid (principal, action == Action::"transfer", resource)
when { context.amount_cents > 10000000 };

@id("forbid-nonpositive-amount")
forbid (principal, action == Action::"transfer", resource)
when { context.amount_cents <= 0 };

@id("forbid-velocity")
forbid (principal, action == Action::"transfer", resource)
when { context.velocity_exceeded };

@id("forbid-kill-switch")
forbid (principal, action == Action::"transfer", resource)
when { context.killed };
