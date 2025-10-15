# Common Clean Architecture Violations

## Overview

This document catalogs the most frequent violations of Clean Architecture principles found in Java applications. Understanding these patterns helps identify and prevent architectural erosion.

## God Classes

### Description
Single classes that mix responsibilities from multiple layers, violating single responsibility principle.

### Example
```java
// BAD: God class mixing all layers
@RestController
public class OrderManager {
    // Direct database access
    @Autowired
    private EntityManager entityManager;
    
    @PostMapping("/orders")
    public Order createOrder(@RequestBody OrderRequest request) {
        // HTTP handling
        if (request == null) {
            throw new BadRequestException();
        }
        
        // Business validation
        if (request.getTotal() < 0) {
            throw new ValidationException("Negative total");
        }
        
        // Business calculation
        double tax = request.getTotal() * 0.08;
        double finalTotal = request.getTotal() + tax;
        
        // Direct database query
        Query query = entityManager.createQuery(
            "SELECT c FROM Customer c WHERE c.id = :id");
        query.setParameter("id", request.getCustomerId());
        Customer customer = (Customer) query.getSingleResult();
        
        // Business rule
        if (customer.getOrderCount() > 10) {
            finalTotal = finalTotal * 0.9;  // Loyalty discount
        }
        
        // Data persistence
        Order order = new Order();
        order.setTotal(finalTotal);
        entityManager.persist(order);
        
        return order;
    }
}
```

### Problems
- Impossible to test layers independently
- Changes in one concern affect entire class
- Violates all layering principles simultaneously
- Cannot reuse business logic outside HTTP context

### Solution
Split into proper layers:

```java
// Controller: HTTP only
@RestController
public class OrderController {
    private final OrderService orderService;
    
    @PostMapping("/orders")
    public Order createOrder(@RequestBody OrderRequest request) {
        return orderService.createOrder(request);
    }
}

// Service: Business logic
@Service
public class OrderService {
    private final OrderRepository orderRepository;
    private final CustomerRepository customerRepository;
    
    public Order createOrder(OrderRequest request) {
        validateOrder(request);
        Customer customer = customerRepository.findById(request.getCustomerId());
        double finalTotal = calculateTotal(request, customer);
        return orderRepository.save(new Order(finalTotal));
    }
}

// Repository: Data access
@Repository
public interface OrderRepository extends JpaRepository<Order, Long> {
}
```

## Leaky Abstractions

### Description
When implementation details from one layer leak into another, creating tight coupling.

### Example: Domain Logic Leaking to Controller

```java
// BAD: Controller knows about domain logic details
@RestController
public class UserController {
    @GetMapping("/users/{id}/status")
    public String getUserStatus(@PathVariable Long id) {
        User user = userRepository.findById(id);
        
        // Controller knows business status calculation
        if (user.getLastLogin().isBefore(LocalDateTime.now().minusDays(30))) {
            return "INACTIVE";
        } else if (user.getSubscriptionEndDate().isBefore(LocalDateTime.now())) {
            return "EXPIRED";
        } else {
            return "ACTIVE";
        }
    }
}
```

### Solution

```java
// Service encapsulates status logic
@Service
public class UserService {
    public UserStatus calculateUserStatus(User user) {
        if (user.getLastLogin().isBefore(LocalDateTime.now().minusDays(30))) {
            return UserStatus.INACTIVE;
        }
        if (user.getSubscriptionEndDate().isBefore(LocalDateTime.now())) {
            return UserStatus.EXPIRED;
        }
        return UserStatus.ACTIVE;
    }
}

// Controller delegates
@RestController
public class UserController {
    @GetMapping("/users/{id}/status")
    public UserStatus getUserStatus(@PathVariable Long id) {
        User user = userService.getUser(id);
        return userService.calculateUserStatus(user);
    }
}
```

## Fat Controllers

### Description
Controllers containing extensive business logic, calculations, or data transformations.

### Example

```java
// BAD: Fat controller with business logic
@RestController
public class ReportController {
    @GetMapping("/reports/sales")
    public SalesReport generateReport(@RequestParam String period) {
        List<Order> orders = orderRepository.findAll();
        
        // Complex business calculation in controller
        double total = 0;
        Map<String, Double> categoryTotals = new HashMap<>();
        
        for (Order order : orders) {
            if (matchesPeriod(order, period)) {
                total += order.getTotal();
                
                for (OrderItem item : order.getItems()) {
                    String category = item.getProduct().getCategory();
                    categoryTotals.merge(category, item.getTotal(), Double::sum);
                }
            }
        }
        
        // More calculations...
        double avgOrderValue = total / orders.size();
        String topCategory = categoryTotals.entrySet().stream()
            .max(Map.Entry.comparingByValue())
            .map(Map.Entry::getKey)
            .orElse("NONE");
        
        return new SalesReport(total, avgOrderValue, topCategory);
    }
}
```

### Solution

```java
// Service handles all business logic
@Service
public class ReportService {
    public SalesReport generateSalesReport(String period) {
        List<Order> orders = getOrdersForPeriod(period);
        double total = calculateTotal(orders);
        double avgOrderValue = calculateAverage(orders);
        String topCategory = findTopCategory(orders);
        return new SalesReport(total, avgOrderValue, topCategory);
    }
}

// Thin controller
@RestController
public class ReportController {
    @GetMapping("/reports/sales")
    public SalesReport generateReport(@RequestParam String period) {
        return reportService.generateSalesReport(period);
    }
}
```

## Transaction Script Anti-Pattern

### Description
Procedural code in controllers or God classes instead of proper object-oriented design with services.

### Example

```java
// BAD: Procedural transaction script
@RestController
public class CheckoutController {
    @PostMapping("/checkout")
    public Receipt processCheckout(@RequestBody Cart cart) {
        // Procedural steps all in controller
        double subtotal = 0;
        for (CartItem item : cart.getItems()) {
            subtotal += item.getPrice() * item.getQuantity();
        }
        
        double discount = 0;
        if (subtotal > 100) {
            discount = subtotal * 0.1;
        }
        
        double tax = (subtotal - discount) * 0.08;
        double shipping = calculateShipping(cart);
        double total = subtotal - discount + tax + shipping;
        
        // More procedural steps...
        return new Receipt(total);
    }
}
```

### Solution

```java
// Proper service-oriented approach
@Service
public class CheckoutService {
    public Receipt processCheckout(Cart cart) {
        CheckoutCalculation calc = new CheckoutCalculation();
        calc.setSubtotal(calculateSubtotal(cart));
        calc.setDiscount(calculateDiscount(calc.getSubtotal()));
        calc.setTax(calculateTax(calc.getSubtotal(), calc.getDiscount()));
        calc.setShipping(calculateShipping(cart));
        return createReceipt(calc);
    }
}
```

## Repository Pattern Violations

### Description
Repositories containing business logic, complex queries with business rules, or data transformations.

### Example

```java
// BAD: Repository with business logic
@Repository
public interface ProductRepository extends JpaRepository<Product, Long> {
    
    // Business concept "bestseller" in repository
    @Query("SELECT p FROM Product p WHERE p.salesCount > 1000 ORDER BY p.salesCount DESC")
    List<Product> findBestsellers();
    
    // Business calculation in query
    @Query("SELECT new ProductDTO(p.id, p.name, p.price * 0.9) FROM Product p")
    List<ProductDTO> findDiscountedProducts();
    
    // Complex business filtering
    default List<Product> findFeaturedProducts() {
        return findAll().stream()
            .filter(p -> p.getRating() > 4.0)
            .filter(p -> p.getStock() > 0)
            .filter(p -> p.isActive())
            .limit(10)
            .toList();
    }
}
```

### Solution

```java
// Clean repository - data access only
@Repository
public interface ProductRepository extends JpaRepository<Product, Long> {
    List<Product> findBySalesCountGreaterThan(int count);
    List<Product> findAllByOrderBySalesCountDesc();
}

// Business logic in service
@Service
public class ProductService {
    private static final int BESTSELLER_THRESHOLD = 1000;
    
    public List<Product> findBestsellers() {
        return productRepository
            .findBySalesCountGreaterThan(BESTSELLER_THRESHOLD);
    }
    
    public List<ProductDTO> findDiscountedProducts() {
        return productRepository.findAll().stream()
            .map(p -> new ProductDTO(p.getId(), p.getName(), 
                                    calculateDiscountedPrice(p)))
            .toList();
    }
    
    public List<Product> findFeaturedProducts() {
        return productRepository.findAll().stream()
            .filter(this::isFeatured)
            .limit(10)
            .toList();
    }
    
    private boolean isFeatured(Product p) {
        return p.getRating() > 4.0 && 
               p.getStock() > 0 && 
               p.isActive();
    }
}
```

## Anemic Service Layer

### Description
Services that are merely pass-through to repositories, adding no business value.

### Example

```java
// BAD: Anemic service - just delegates to repository
@Service
public class ProductService {
    private final ProductRepository productRepository;
    
    public List<Product> findAll() {
        return productRepository.findAll();
    }
    
    public Product findById(Long id) {
        return productRepository.findById(id).orElse(null);
    }
    
    public Product save(Product product) {
        return productRepository.save(product);
    }
    
    // No business logic anywhere!
}
```

### Problems
- Service adds no value
- Business logic ends up in controllers or entities
- Missing layer for business rules

### Solution

```java
// Rich service with business logic
@Service
public class ProductService {
    public Product getProduct(Long id) {
        return productRepository.findById(id)
            .orElseThrow(() -> new ProductNotFoundException(id));
    }
    
    public Product createProduct(ProductRequest request) {
        validateProduct(request);
        checkDuplicateName(request.getName());
        Product product = mapToEntity(request);
        return productRepository.save(product);
    }
    
    public List<Product> getAvailableProducts() {
        return productRepository.findAll().stream()
            .filter(this::isAvailable)
            .collect(Collectors.toList());
    }
    
    private boolean isAvailable(Product p) {
        return p.getStock() > 0 && p.isActive();
    }
    
    private void validateProduct(ProductRequest request) {
        if (request.getPrice() < 0) {
            throw new InvalidPriceException();
        }
    }
}
```

## Direct Entity Exposure

### Description
Exposing JPA entities directly through REST endpoints without DTOs.

### Example

```java
// BAD: Entity exposed directly
@RestController
public class UserController {
    @GetMapping("/users/{id}")
    public User getUser(@PathVariable Long id) {
        return userRepository.findById(id).orElseThrow();  // Exposes entity
    }
}

@Entity
public class User {
    private String password;  // Sensitive field exposed!
    private String ssn;       // Sensitive field exposed!
    // ...
}
```

### Problems
- Exposes internal structure
- May leak sensitive data
- Tight coupling between API and persistence
- Cannot evolve API independently

### Solution

```java
// Use DTOs
@RestController
public class UserController {
    @GetMapping("/users/{id}")
    public UserDTO getUser(@PathVariable Long id) {
        User user = userService.getUser(id);
        return UserMapper.toDTO(user);
    }
}

public class UserDTO {
    private Long id;
    private String name;
    private String email;
    // No sensitive fields
}
```

## Summary of Violations and Solutions

| Violation | Symptom | Solution |
|-----------|---------|----------|
| God Class | One class does everything | Split into separate layers |
| Leaky Abstraction | Layer knows too much about others | Use interfaces, hide implementation |
| Fat Controller | Business logic in controller | Move to service layer |
| Transaction Script | Procedural code everywhere | Object-oriented services |
| Repository Violation | Business logic in repo | Keep repos data-only |
| Anemic Service | Services just delegate | Add business logic to services |
| Direct Entity Exposure | JPA entities in API | Use DTOs |

## Detection Checklist

When reviewing code, ask:

1. **Controllers:** Do they contain any if-statements, loops, or calculations?
2. **Services:** Do they implement actual business logic or just delegate?
3. **Repositories:** Do methods have business concepts in names?
4. **Entities:** Do they have methods beyond getters/setters?
5. **General:** Can business logic be tested without HTTP or database?

If the answer violates these principles, refactoring is needed to restore proper layering.