"""
Importar todos los modelos aca para que Alembic (autogenerate) y Base.metadata
los vean todos. Si se agrega un modelo nuevo en el futuro, importarlo aca tambien.
"""
from app.models.security import User, Role, UserRole  # noqa: F401
from app.models.catalog import (  # noqa: F401
    Provider,
    ProviderAlias,
    ExpenseCategory,
    Area,
    AreaAlias,
    CostCenter,
    BusinessUnit,
    Company,
    Branch,
    EconomicGroup,
    Project,
)
from app.models.importing import (  # noqa: F401
    ImportTemplate,
    ImportTemplateVersion,
    ImportFile,
    ImportBatch,
    StagingInvoice,
    ValidationError,
    ValidationRule,
)
from app.models.invoicing import Invoice, InvoiceLine  # noqa: F401
from app.models.budget import Budget, BudgetVersion  # noqa: F401
from app.models.audit import AuditEvent  # noqa: F401
from app.models.requirements import Requirement, RequirementComment, Attachment  # noqa: F401
