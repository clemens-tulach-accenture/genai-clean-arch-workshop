# Clean Architecture: Layering Principles

## Overview

Clean Architecture enforces strict separation of concerns through well-defined layers. Each layer has specific responsibilities and constraints to ensure maintainability, testability, and scalability.

## Core Principles

### Dependency Rule
Dependencies must point inward. Outer layers can depend on inner layers, but inner layers must never depend on outer layers.

**Layer Hierarchy (outer to inner):**
1. UI/Controller Layer (outermost)
2. Service Layer
3. Domain Layer (innermost)
4. Repository Layer (infrastructure, depends on domain)

### Single Responsibility Principle
Each layer handles exactly one type of concern:
- Controllers: HTTP/API concerns
- Services: Business logic
- Repositories: Data persistence
- Entities: Domain concepts

## Layer Definitions

### Domain Layer (Core)
**Purpose:** Contains business entities, rules, and domain logic independent of frameworks.

**Contains:**
- Business entities (POJOs/entities)
- Domain logic and invariants
- Value objects
- Domain events

**Constraints:**
- No dependencies on outer layers
- No framework-specific annotations (except unavoidable JPA mappings)
- Pure business logic only
- No knowledge of databases, HTTP, or UI

### Service Layer
**Purpose:** Implements business use cases by orchestrating domain objects.

**Contains:**
- Use case implementations
- Business rule orchestration
- Transaction management
- Business validations and calculations
- Workflow coordination

**Constraints:**
- Must not contain persistence logic
- Must not contain HTTP/REST logic
- Should delegate to domain objects when possible
- No direct database queries

### Controller/API Layer
**Purpose:** Handles incoming requests, parses input, calls services, returns responses.

**Contains:**
- Request/response handling
- Input validation (format only, not business rules)
- HTTP status code mapping
- DTO/Entity conversion
- Delegation to services

**Constraints:**
- No business calculations or decisions
- No direct repository access
- No database queries
- Thin layer with minimal logic

### Repository Layer
**Purpose:** Manages data persistence through CRUD operations only.

**Contains:**
- Data access operations (CRUD)
- Query execution
- Entity persistence
- Data retrieval

**Constraints:**
- No business logic
- No data transformations based on business rules
- No filtering or sorting based on business conditions
- Pure data access only

## Benefits

### Maintainability
- Clear boundaries make code easier to understand
- Changes to business rules affect only service layer
- Each layer can be modified independently

### Testability
- Services can be unit tested with mock repositories
- Controllers can be tested without business logic complexity
- Each layer verifiable in isolation

### Scalability
- Stateless services scale horizontally
- Teams can work on different layers concurrently
- Services reusable across multiple interfaces (REST, GraphQL, CLI)

### Evolvability
- Swap frameworks without touching business logic
- Business rules evolve in centralized service layer
- Well-defined layers make refactoring safer

## Summary

Proper layering prevents architectural erosion by enforcing clear boundaries. Each layer focuses on its specific concern, making the system easier to understand, test, and maintain over time.