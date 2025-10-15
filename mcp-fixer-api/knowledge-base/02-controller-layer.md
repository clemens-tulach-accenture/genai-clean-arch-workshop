# Controller Layer Best Practices

## Purpose

The controller layer handles HTTP/API concerns only. It acts as a thin adapter between the external world (HTTP requests) and the service layer. Controllers should contain no business logic.

## Responsibilities

### What Controllers Should Do
- Accept HTTP requests and extract parameters
- Perform input format validation only (not business validation)
- Delegate all business operations to services
- Map service results to HTTP responses
- Handle HTTP-specific concerns (status codes, headers, content negotiation)

### What Controllers Must Not Do
- Perform business calculations
- Make business decisions
- Access repositories directly
- Contain business validation logic
- Transform data based on business rules

## Violation Example: Business Logic in Controller

```java
@RestController
public class UserController {
    @Autowired
    private UserRepository userRepository;
    
    @GetMapping("/users/{id}")
    public User getUser(@PathVariable Long id) {
        User user = userRepository.findById(id);
        
        // VIOLATION: Business validation in controller
        if (user.getAge() < 18) {
            throw new RuntimeException("User is minor");
        }
        
        // VIOLATION: Business calculation in controller
        user.setDiscount(user.getAge() > 65 ? 0.2 : 0.0);
        
        return user;
    }
}
```

**Problems:**
- Age validation is a business rule, not HTTP concern
- Discount calculation is business logic
- Direct repository access bypasses service layer
- Hard to test without HTTP context
- Business rules duplicated across endpoints

## Correct Implementation

```java
@RestController
@RequestMapping("/api/users")
public class UserController {
    private final UserService userService;
    
    @Autowired
    public UserController(UserService userService) {
        this.userService = userService;
    }
    
    @GetMapping("/{id}")
    public ResponseEntity<User> getUser(@PathVariable Long id) {
        // Simple delegation - no business logic
        User user = userService.getValidatedUser(id);
        return ResponseEntity.ok(user);
    }
    
    @PostMapping
    public ResponseEntity<User> createUser(@RequestBody UserRequest request) {
        // Format validation only
        if (request == null || request.getName() == null) {
            return ResponseEntity.badRequest().build();
        }
        
        // Business validation happens in service
        User user = userService.createUser(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(user);
    }
    
    @GetMapping("/{id}/discounted-price")
    public ResponseEntity<PriceResponse> getDiscountedPrice(@PathVariable Long id) {
        // Controller extracts ID, service performs calculation
        double price = userService.calculateDiscountedPrice(id);
        return ResponseEntity.ok(new PriceResponse(price));
    }
}
```

## Common Anti-Patterns

### Pattern 1: Direct Repository Access
```java
// BAD
@RestController
public class ProductController {
    @Autowired
    private ProductRepository productRepository;
    
    @GetMapping("/products/{id}")
    public Product get(@PathVariable Long id) {
        return productRepository.findById(id).orElseThrow();
    }
}

// GOOD
@RestController
public class ProductController {
    @Autowired
    private ProductService productService;
    
    @GetMapping("/products/{id}")
    public Product get(@PathVariable Long id) {
        return productService.getProduct(id);
    }
}
```

### Pattern 2: Business Validation in Controller
```java
// BAD
@PostMapping("/orders")
public Order createOrder(@RequestBody Order order) {
    if (order.getTotal() < 0) {  // Business validation
        throw new IllegalArgumentException("Negative total");
    }
    return orderRepository.save(order);
}

// GOOD
@PostMapping("/orders")
public Order createOrder(@RequestBody Order order) {
    return orderService.createOrder(order);  // Service validates
}
```

### Pattern 3: Business Calculations in Controller
```java
// BAD
@GetMapping("/orders/summary")
public OrderSummary getSummary() {
    List<Order> orders = orderRepository.findAll();
    double total = orders.stream()
        .mapToDouble(Order::getTotal)  // Business calculation
        .sum();
    return new OrderSummary(total);
}

// GOOD
@GetMapping("/orders/summary")
public OrderSummary getSummary() {
    return orderService.calculateSummary();  // Service calculates
}
```

## Key Principles

### Thin Controllers
Controllers should be as thin as possible, typically 3-5 lines per method:
1. Extract parameters from request
2. Call service method
3. Return HTTP response

### Dependency Injection
Always inject services through constructor, never instantiate directly.

### Exception Handling
Let service layer throw business exceptions, handle HTTP mapping in controller advice or exception handlers.

### DTOs for Input/Output
Use Data Transfer Objects for request/response, not domain entities directly when they contain sensitive data or require transformation.

## Impact of Violations

### On Testing
- Requires HTTP server setup for testing business logic
- Cannot unit test business rules independently
- Integration tests become slow and fragile

### On Maintenance
- Business logic scattered across multiple controllers
- Changes to business rules require updating many endpoints
- Difficult to trace where business rules are implemented

### On Reusability
- Cannot reuse business logic for CLI, GraphQL, or batch processing
- Each interface duplicates business logic
- Inconsistent behavior across different endpoints

## Summary

Controllers must remain thin adapters between HTTP and business logic. All business decisions, calculations, and validations belong in the service layer. This separation ensures testability, maintainability, and reusability of business logic across different interfaces.