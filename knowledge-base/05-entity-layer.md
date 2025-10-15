# Entity Layer Best Practices

## Purpose

Entities represent domain concepts and data structures. They should be simple data containers with minimal logic. Complex business calculations and transformations belong in the service layer, not in entities.

## Responsibilities

### What Entities Should Contain
- Simple getters and setters
- Data structure definition
- Basic data integrity constraints
- Equality and hash code methods
- Simple helper methods for intrinsic properties

### What Entities Must Not Contain
- Complex business calculations
- Business rule validations
- Dependencies on services or repositories
- External API calls
- Decisions based on external state

## Correct Entity Implementation

```java
@Entity
@Table(name = "products")
public class Product {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(nullable = false)
    private String name;
    
    @Column(nullable = false)
    private double price;
    
    @Column(name = "stock_quantity")
    private int stockQuantity;
    
    @Column(name = "created_at")
    private LocalDateTime createdAt;
    
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;
    
    // Constructors
    public Product() {
        this.createdAt = LocalDateTime.now();
        this.updatedAt = LocalDateTime.now();
    }
    
    public Product(String name, double price) {
        this();
        this.name = name;
        this.price = price;
    }
    
    // Simple getters and setters
    public Long getId() {
        return id;
    }
    
    public void setId(Long id) {
        this.id = id;
    }
    
    public String getName() {
        return name;
    }
    
    public void setName(String name) {
        this.name = name;
    }
    
    public double getPrice() {
        return price;
    }
    
    public void setPrice(double price) {
        this.price = price;
    }
    
    public int getStockQuantity() {
        return stockQuantity;
    }
    
    public void setStockQuantity(int stockQuantity) {
        this.stockQuantity = stockQuantity;
    }
    
    // Lifecycle callbacks for framework concerns only
    @PreUpdate
    protected void onUpdate() {
        this.updatedAt = LocalDateTime.now();
    }
    
    // Equality based on business key
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Product product = (Product) o;
        return Objects.equals(id, product.id);
    }
    
    @Override
    public int hashCode() {
        return Objects.hash(id);
    }
    
    @Override
    public String toString() {
        return "Product{id=" + id + ", name='" + name + "', price=" + price + "}";
    }
}
```

**Key Points:**
- Simple data container
- No business calculations
- No external dependencies
- Framework callbacks only for persistence lifecycle

## Violation: Business Logic in Entity

```java
// BAD: Entity with business calculations
@Entity
public class Order {
    @Id
    private Long id;
    private double total;
    private String status;
    
    // VIOLATION: Business calculation in entity getter
    public double getDiscountedTotal() {
        if (total > 100) {
            return total * 0.9;  // 10% discount - business rule
        }
        return total;
    }
    
    // VIOLATION: Business decision in entity method
    public boolean isEligibleForFreeShipping() {
        return total > 50 && status.equals("ACTIVE");  // Business rules
    }
    
    // VIOLATION: Complex business logic
    public double calculateTax() {
        double taxRate = 0.0;
        if (total > 1000) {
            taxRate = 0.15;  // Business rule: high-value orders
        } else if (total > 100) {
            taxRate = 0.10;  // Business rule: medium-value orders
        } else {
            taxRate = 0.08;  // Business rule: low-value orders
        }
        return total * taxRate;
    }
}
```

**Problems:**
- Business calculations embedded in entity
- Business rules scattered across getters
- Hard to test business logic independently
- Cannot change business rules without modifying entity
- Business knowledge leaked into data layer

## Correct Implementation: Move Logic to Service

```java
// GOOD: Simple entity with no business logic
@Entity
public class Order {
    @Id
    private Long id;
    private double total;
    private String status;
    
    // Simple getters only
    public Long getId() { return id; }
    public double getTotal() { return total; }
    public String getStatus() { return status; }
    
    public void setId(Long id) { this.id = id; }
    public void setTotal(double total) { this.total = total; }
    public void setStatus(String status) { this.status = status; }
}

// GOOD: Business logic in service
@Service
public class OrderService {
    
    // Business calculation
    public double calculateDiscountedTotal(Order order) {
        if (order.getTotal() > 100) {
            return order.getTotal() * 0.9;
        }
        return order.getTotal();
    }
    
    // Business rule
    public boolean isEligibleForFreeShipping(Order order) {
        return order.getTotal() > 50 && 
               OrderStatus.ACTIVE.name().equals(order.getStatus());
    }
    
    // Business calculation
    public double calculateTax(Order order) {
        double total = order.getTotal();
        double taxRate;
        
        if (total > 1000) {
            taxRate = TAX_RATE_HIGH;
        } else if (total > 100) {
            taxRate = TAX_RATE_MEDIUM;
        } else {
            taxRate = TAX_RATE_LOW;
        }
        
        return total * taxRate;
    }
}
```

## Anemic vs Rich Domain Model

### Anemic Domain Model (Preferred for Most Cases)
Entities are simple data containers. Business logic in services.

```java
// Anemic entity
@Entity
public class Invoice {
    private double subtotal;
    private double taxRate;
    
    public double getSubtotal() { return subtotal; }
    public double getTaxRate() { return taxRate; }
}

// Business logic in service
@Service
public class InvoiceService {
    public double calculateTotal(Invoice invoice) {
        return invoice.getSubtotal() * (1 + invoice.getTaxRate());
    }
}
```

**When to use:** Most business applications, especially with Spring/JPA

### Rich Domain Model (Use with Caution)
Entities contain domain behavior, but only intrinsic operations.

```java
// Rich entity - acceptable for simple intrinsic behavior
@Entity
public class Money {
    private double amount;
    private String currency;
    
    public Money add(Money other) {
        if (!this.currency.equals(other.currency)) {
            throw new IllegalArgumentException("Currency mismatch");
        }
        return new Money(this.amount + other.amount, this.currency);
    }
}
```

**When to use:** Domain-Driven Design with aggregate roots, when entity behavior is intrinsic and self-contained

### The Boundary
Entity methods are acceptable only if:
- They operate on entity's own data only
- They do not call services or repositories
- They do not depend on external state
- They represent intrinsic domain operations

```java
// ACCEPTABLE: Intrinsic operations
public class DateRange {
    private LocalDate start;
    private LocalDate end;
    
    public boolean contains(LocalDate date) {
        return !date.isBefore(start) && !date.isAfter(end);
    }
    
    public long getDays() {
        return ChronoUnit.DAYS.between(start, end);
    }
}

// NOT ACCEPTABLE: External dependencies
public class Order {
    public boolean canBeCancelled(OrderService orderService) {
        return orderService.checkCancellationPolicy(this);  // WRONG
    }
}
```

## Common Anti-Patterns

### Anti-Pattern 1: Calculations in Getters

```java
// BAD: Calculation in getter
public class Product {
    private double price;
    
    public double getDiscountedPrice() {
        return price * 0.9;  // Business calculation
    }
}

// GOOD: Simple getter, calculation in service
public class Product {
    private double price;
    
    public double getPrice() {
        return price;
    }
}

@Service
public class PricingService {
    public double calculateDiscountedPrice(Product product) {
        return product.getPrice() * 0.9;
    }
}
```

### Anti-Pattern 2: Status-Based Logic in Entity

```java
// BAD: Business decisions based on status
public class Order {
    private OrderStatus status;
    
    public boolean canBeModified() {
        return status == OrderStatus.DRAFT || 
               status == OrderStatus.PENDING;  // Business rule
    }
}

// GOOD: Decision logic in service
@Service
public class OrderService {
    public boolean canModifyOrder(Order order) {
        OrderStatus status = order.getStatus();
        return status == OrderStatus.DRAFT || 
               status == OrderStatus.PENDING;
    }
}
```

### Anti-Pattern 3: Validation Logic in Entity

```java
// BAD: Business validation in entity
public class User {
    private int age;
    
    public void setAge(int age) {
        if (age < 18) {  // Business rule
            throw new IllegalArgumentException("User must be adult");
        }
        this.age = age;
    }
}

// GOOD: Validation in service
public class User {
    private int age;
    
    public void setAge(int age) {
        this.age = age;  // Simple setter
    }
}

@Service
public class UserService {
    public void createUser(UserRequest request) {
        if (request.getAge() < 18) {
            throw new ValidationException("User must be adult");
        }
        User user = new User();
        user.setAge(request.getAge());
        return userRepository.save(user);
    }
}
```

## When to Keep Logic in Entities

Acceptable cases for entity logic:

### 1. Formatting and Presentation Helpers
```java
public String getFormattedPrice() {
    return String.format("$%.2f", price);
}
```

### 2. Derived Simple Properties
```java
public String getFullName() {
    return firstName + " " + lastName;
}
```

### 3. Collection Helpers
```java
public void addItem(OrderItem item) {
    if (items == null) {
        items = new ArrayList<>();
    }
    items.add(item);
    item.setOrder(this);
}
```

### 4. Validation of Intrinsic Constraints
```java
public void setEmail(String email) {
    if (email != null && !email.contains("@")) {
        throw new IllegalArgumentException("Invalid email format");
    }
    this.email = email;
}
```

**Note:** Even these are debatable. Formatting belongs in view layer, validation in service layer.

## Testing Entities

Entity tests should verify data structure, not business logic.

```java
class ProductTest {
    @Test
    void shouldCreateProductWithRequiredFields() {
        Product product = new Product("Test", 100.0);
        
        assertNotNull(product);
        assertEquals("Test", product.getName());
        assertEquals(100.0, product.getPrice());
    }
    
    @Test
    void shouldUpdateTimestampOnModification() {
        Product product = new Product("Test", 100.0);
        LocalDateTime before = product.getUpdatedAt();
        
        product.setPrice(150.0);
        product.onUpdate();
        
        assertTrue(product.getUpdatedAt().isAfter(before));
    }
    
    // NO business logic tests - those belong in service tests
}
```

## Summary

Entities should be simple data containers with minimal logic. Complex calculations, business rules, and validations belong in the service layer. This separation ensures:

- Business logic is testable independently
- Entities remain reusable across use cases
- Business rules are centralized in services
- Changes to business logic do not affect data structures
- Clear separation between data and behavior

Keep entities anemic in most cases. Only add logic to entities when it is truly intrinsic to the domain concept and operates solely on the entity's own data.