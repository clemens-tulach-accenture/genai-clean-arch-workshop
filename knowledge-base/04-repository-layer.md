# Repository Layer Best Practices

## Purpose

The repository layer provides a clean abstraction for data access. It handles CRUD operations and query execution without any business logic. Repositories translate between domain objects and persistence mechanisms.

## Responsibilities

### What Repositories Should Do
- Provide CRUD operations (Create, Read, Update, Delete)
- Execute database queries
- Persist and retrieve entities
- Return raw data without transformations
- Handle data access concerns only

### What Repositories Must Not Do
- Contain business logic or calculations
- Perform data transformations based on business rules
- Filter or sort based on business conditions
- Make business decisions
- Validate business rules

## Correct Repository Implementation

```java
@Repository
public interface ProductRepository extends JpaRepository<Product, Long> {
    
    // Standard CRUD inherited from JpaRepository:
    // - findById(Long id)
    // - findAll()
    // - save(Product product)
    // - delete(Product product)
    // - count()
    
    // Simple data access queries - no business logic
    Optional<Product> findByName(String name);
    
    List<Product> findByPriceGreaterThan(double price);
    
    List<Product> findByPriceLessThan(double price);
    
    List<Product> findByPriceBetween(double minPrice, double maxPrice);
    
    List<Product> findByStockQuantityGreaterThan(int quantity);
    
    List<Product> findByCreatedAtAfter(LocalDateTime date);
    
    // Custom JPQL query - still pure data access
    @Query("SELECT p FROM Product p WHERE p.name LIKE %:keyword%")
    List<Product> searchByKeyword(@Param("keyword") String keyword);
    
    // Count and existence checks - data access only
    long countByPriceGreaterThan(double price);
    
    boolean existsByName(String name);
}
```

**Key Points:**
- All methods are pure data access
- No business logic in queries
- Repository returns raw data
- Service layer applies business rules

## Violation: Business Logic in Repository

```java
// BAD: Repository with business logic
@Repository
public interface OrderRepository extends JpaRepository<Order, Long> {
    
    // VIOLATION: "Eligible" is a business concept
    @Query("SELECT o FROM Order o WHERE o.total > 100 AND o.status = 'ACTIVE'")
    List<Order> findEligibleOrders();
    
    // VIOLATION: Business logic in default method
    default List<Order> findEligibleForDiscount() {
        List<Order> orders = findAll();
        return orders.stream()
            .filter(order -> order.getTotal() > 100)  // Business rule
            .peek(order -> order.setTotal(order.getTotal() * 0.9))  // Business calculation
            .toList();
    }
    
    // VIOLATION: Business transformation in query
    @Query("SELECT new OrderDTO(o.id, o.total * 0.9) FROM Order o WHERE o.total > 100")
    List<OrderDTO> findDiscountedOrders();
}
```

**Problems:**
- Business rules (eligibility, discount) in repository
- Data transformations based on business logic
- Filtering based on business conditions
- Repository knows too much about business domain

## Correct Implementation: Move Logic to Service

```java
// GOOD: Repository with pure data access
@Repository
public interface OrderRepository extends JpaRepository<Order, Long> {
    List<Order> findAll();
    List<Order> findByTotalGreaterThan(double threshold);
}

// GOOD: Service contains business logic
@Service
public class OrderService {
    private final OrderRepository orderRepository;
    
    public List<Order> findEligibleOrders() {
        // Business rule: eligible means total > 100 and active
        return orderRepository.findAll().stream()
            .filter(order -> order.getTotal() > 100)
            .filter(order -> order.getStatus() == OrderStatus.ACTIVE)
            .collect(Collectors.toList());
    }
    
    public List<Order> findOrdersWithDiscounts() {
        List<Order> eligible = findEligibleOrders();
        return eligible.stream()
            .map(order -> applyDiscount(order))
            .collect(Collectors.toList());
    }
    
    private Order applyDiscount(Order order) {
        // Business calculation in service, not repository
        double discountedTotal = order.getTotal() * 0.9;
        order.setDiscountedTotal(discountedTotal);
        return order;
    }
}
```

## Common Anti-Patterns

### Anti-Pattern 1: Filtering Based on Business Rules

```java
// BAD: Business condition in repository
default List<Product> findPremiumProducts() {
    return findAll().stream()
        .filter(p -> p.getPrice() > 500)  // "Premium" is business concept
        .toList();
}

// GOOD: Repository provides data, service applies rule
// Repository:
List<Product> findByPriceGreaterThan(double price);

// Service:
public List<Product> findPremiumProducts() {
    return productRepository.findByPriceGreaterThan(PREMIUM_THRESHOLD);
}
```

### Anti-Pattern 2: Data Mutation in Repository

```java
// BAD: Repository mutating entities based on business rules
default User findValidatedById(Long id) {
    User user = findById(id).orElseThrow();
    if (user.getBalance() < 0) {  // Business rule
        user.setStatus("overdue");  // Business decision
    }
    return user;
}

// GOOD: Repository returns raw data, service handles business logic
// Repository:
Optional<User> findById(Long id);

// Service:
public User getValidatedUser(Long id) {
    User user = userRepository.findById(id).orElseThrow();
    if (user.getBalance() < 0) {
        user.setStatus("overdue");
    }
    return user;
}
```

### Anti-Pattern 3: Complex Business Queries

```java
// BAD: Business logic embedded in JPQL
@Query("SELECT o FROM Order o WHERE " +
       "o.total > :minTotal AND " +
       "o.status = 'ACTIVE' AND " +
       "o.customer.loyaltyPoints > 1000")  // Multiple business rules
List<Order> findVIPOrders(@Param("minTotal") double minTotal);

// GOOD: Simple data access, business logic in service
// Repository:
List<Order> findByTotalGreaterThan(double total);
List<Order> findByStatus(OrderStatus status);

// Service:
public List<Order> findVIPOrders() {
    return orderRepository.findByStatus(OrderStatus.ACTIVE).stream()
        .filter(order -> order.getTotal() > MIN_VIP_TOTAL)
        .filter(order -> order.getCustomer().getLoyaltyPoints() > VIP_POINTS_THRESHOLD)
        .collect(Collectors.toList());
}
```

## When Business Logic Appears to be Data Access

Sometimes business rules manifest as query conditions. The key is: if the condition represents a business concept, it belongs in the service layer.

### Example: "Active" Orders

```java
// Seems like data access, but "active" might be a business concept
List<Order> findByStatus(OrderStatus status);  // OK - generic data access

// If "active" has business meaning beyond just status field:
@Service
public class OrderService {
    public List<Order> findActiveOrders() {
        // Business rule: active means PENDING or PROCESSING, not CANCELLED
        return orderRepository.findAll().stream()
            .filter(order -> order.getStatus() == PENDING || 
                           order.getStatus() == PROCESSING)
            .collect(Collectors.toList());
    }
}
```

## Query Methods vs Custom Logic

Spring Data JPA query methods are acceptable when they perform pure data access.

```java
// GOOD: Pure data access patterns
List<Product> findByCategory(String category);
List<Product> findByPriceBetween(double min, double max);
List<Product> findByNameContaining(String keyword);
Optional<Product> findFirstByOrderByCreatedAtDesc();

// QUESTIONABLE: May contain implicit business logic
List<Order> findEligibleOrders();  // What makes an order "eligible"?
List<Product> findFeaturedProducts();  // What is "featured"?
List<User> findActiveUsers();  // What is "active"?

// If these involve business rules, move to service
```

## Performance Considerations

Repositories can use database-level operations for performance, but must not include business logic.

```java
// GOOD: Efficient data access without business logic
@Query("SELECT p FROM Product p WHERE p.price > :threshold")
List<Product> findExpensiveProducts(@Param("threshold") double threshold);

// Service determines what "expensive" means
public List<Product> findExpensiveProducts() {
    return productRepository.findExpensiveProducts(EXPENSIVE_THRESHOLD);
}

// BAD: Business calculation in database query
@Query("SELECT p FROM Product p WHERE p.price * 0.9 > :target")
List<Product> findProductsWithDiscountAbove(@Param("target") double target);
```

## Testing Repositories

Repository tests should verify data access, not business logic.

```java
@DataJpaTest
class ProductRepositoryTest {
    @Autowired
    private ProductRepository productRepository;
    
    @Test
    void shouldFindProductsByPriceRange() {
        // Arrange
        productRepository.save(new Product("Cheap", 50));
        productRepository.save(new Product("Expensive", 500));
        
        // Act
        List<Product> result = productRepository.findByPriceBetween(100, 600);
        
        // Assert
        assertEquals(1, result.size());
        assertEquals("Expensive", result.get(0).getName());
    }
    
    // No tests for business logic - that belongs in service tests
}
```

## Summary

Repositories must focus exclusively on data access. They should not contain business logic, perform business transformations, or make business decisions. All filtering, validation, and calculations based on business rules belong in the service layer. This separation ensures:

- Business logic is centralized and testable
- Repositories remain reusable across use cases
- Data access concerns are isolated from business concerns
- Changes to business rules do not affect data access layer