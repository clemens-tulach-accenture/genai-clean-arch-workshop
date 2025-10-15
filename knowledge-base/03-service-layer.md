# Service Layer Best Practices

## Purpose

The service layer is the heart of business logic. It implements use cases by orchestrating domain objects and repositories. All business rules, validations, and calculations reside here.

## Responsibilities

### What Services Should Do
- Implement all business use cases
- Perform business validations and calculations
- Orchestrate repositories and domain objects
- Handle transaction boundaries
- Enforce business rules and constraints
- Coordinate complex workflows

### What Services Must Not Do
- Handle HTTP requests or responses
- Contain database-specific implementation details
- Know about presentation layer (views, DTOs)
- Perform data access operations directly (use repositories)

## Correct Service Implementation

```java
@Service
@Transactional
public class ProductService {
    private final ProductRepository productRepository;
    
    @Autowired
    public ProductService(ProductRepository productRepository) {
        this.productRepository = productRepository;
    }
    
    // Business use case: Get product with validation
    public Product getProduct(Long id) {
        return productRepository.findById(id)
            .orElseThrow(() -> new ProductNotFoundException("Product not found: " + id));
    }
    
    // Business use case: Create product with business validation
    public Product createProduct(ProductRequest request) {
        // Business validation
        validateProductRequest(request);
        
        // Business constraint: unique name
        if (productRepository.existsByName(request.getName())) {
            throw new DuplicateProductException("Product exists: " + request.getName());
        }
        
        Product product = new Product(request.getName(), request.getPrice());
        return productRepository.save(product);
    }
    
    // Business rule: Products with price > 100 are eligible for discount
    public List<Product> getEligibleProductsForDiscount() {
        List<Product> allProducts = productRepository.findAll();
        return allProducts.stream()
            .filter(this::isEligibleForDiscount)
            .collect(Collectors.toList());
    }
    
    // Business rule encapsulated in method
    public boolean isEligibleForDiscount(Product product) {
        return product.getPrice() > 100;
    }
    
    // Business calculation: 10% discount for eligible products
    public double calculateDiscountedPrice(Product product) {
        if (isEligibleForDiscount(product)) {
            return product.getPrice() * 0.9;
        }
        return product.getPrice();
    }
    
    // Business rule: Cannot delete products with stock
    public void deleteProduct(Long id) {
        Product product = getProduct(id);
        
        if (product.getStockQuantity() > 0) {
            throw new IllegalStateException("Cannot delete product with stock");
        }
        
        productRepository.delete(product);
    }
    
    // Private business validation
    private void validateProductRequest(ProductRequest request) {
        if (request.getName() == null || request.getName().trim().isEmpty()) {
            throw new InvalidProductException("Product name required");
        }
        if (request.getPrice() < 0) {
            throw new InvalidProductException("Price cannot be negative");
        }
        if (request.getPrice() > 100000) {
            throw new InvalidProductException("Price exceeds maximum");
        }
    }
}
```

## Anti-Pattern: Missing Service Layer

```java
// BAD: Controller directly accessing repository with business logic
@RestController
public class OrderController {
    @Autowired
    private OrderRepository orderRepository;
    
    @GetMapping("/orders/eligible")
    public List<Order> getEligibleOrders() {
        List<Order> orders = orderRepository.findAll();
        
        // Business logic in controller - WRONG!
        for (Order order : orders) {
            if (order.getTotal() > 500) {
                order.setTotal(order.getTotal() * 0.95);
            }
        }
        return orders;
    }
}

// GOOD: Service layer contains business logic
@Service
public class OrderService {
    private final OrderRepository orderRepository;
    
    public List<Order> getEligibleOrders() {
        List<Order> orders = orderRepository.findAll();
        return orders.stream()
            .filter(order -> order.getTotal() > 100)
            .collect(Collectors.toList());
    }
    
    public double applyVipDiscount(Order order) {
        if (order.getTotal() > 500) {
            return order.getTotal() * 0.95;
        }
        return order.getTotal();
    }
}

@RestController
public class OrderController {
    @Autowired
    private OrderService orderService;
    
    @GetMapping("/orders/eligible")
    public List<Order> getEligibleOrders() {
        return orderService.getEligibleOrders();
    }
}
```

## Business Logic Patterns

### Pattern 1: Validation Logic
All business validation belongs in services, not controllers or entities.

```java
public Product createProduct(ProductRequest request) {
    // Business validations
    if (request.getPrice() < minimumPrice) {
        throw new InvalidPriceException("Price below minimum");
    }
    
    if (isDuplicateName(request.getName())) {
        throw new DuplicateNameException("Name already exists");
    }
    
    return productRepository.save(new Product(request));
}
```

### Pattern 2: Business Calculations
All calculations based on business rules belong in services.

```java
public double calculateTotalPrice(Order order) {
    double subtotal = order.getItems().stream()
        .mapToDouble(item -> item.getPrice() * item.getQuantity())
        .sum();
    
    double tax = subtotal * TAX_RATE;
    double shipping = calculateShipping(order);
    
    return subtotal + tax + shipping;
}
```

### Pattern 3: Workflow Orchestration
Services coordinate complex multi-step workflows.

```java
public Order processOrder(OrderRequest request) {
    // Step 1: Validate
    validateOrder(request);
    
    // Step 2: Check inventory
    reserveInventory(request.getItems());
    
    // Step 3: Calculate pricing
    double total = calculateTotalWithDiscounts(request);
    
    // Step 4: Create order
    Order order = new Order(request, total);
    
    // Step 5: Save
    return orderRepository.save(order);
}
```

### Pattern 4: Business Queries
Services translate business queries into repository calls.

```java
public List<Product> findLowStockProducts() {
    // Business rule: low stock means quantity < 10
    return productRepository.findByStockQuantityLessThan(10);
}

public List<Order> findPendingOrders() {
    // Business rule: pending means created < 24h ago and not processed
    LocalDateTime yesterday = LocalDateTime.now().minusDays(1);
    return orderRepository.findByCreatedAtAfterAndStatusNot(yesterday, PROCESSED);
}
```

## Transaction Management

Services are the natural boundary for transactions.

```java
@Transactional
public void transferStock(Long fromProductId, Long toProductId, int quantity) {
    Product from = getProduct(fromProductId);
    Product to = getProduct(toProductId);
    
    // Business validation
    if (from.getStockQuantity() < quantity) {
        throw new InsufficientStockException();
    }
    
    // Atomic operation
    from.setStockQuantity(from.getStockQuantity() - quantity);
    to.setStockQuantity(to.getStockQuantity() + quantity);
    
    productRepository.save(from);
    productRepository.save(to);
}
```

## Business Exceptions

Services throw business-specific exceptions, not technical exceptions.

```java
public class ProductService {
    public Product getProduct(Long id) {
        return productRepository.findById(id)
            .orElseThrow(() -> new ProductNotFoundException(id));
    }
    
    // Business exceptions
    public static class ProductNotFoundException extends RuntimeException {
        public ProductNotFoundException(Long id) {
            super("Product not found: " + id);
        }
    }
    
    public static class InsufficientStockException extends RuntimeException {
        public InsufficientStockException() {
            super("Insufficient stock for operation");
        }
    }
}
```

## Testing Services

Services should be unit tested with mock repositories.

```java
@ExtendWith(MockitoExtension.class)
class ProductServiceTest {
    @Mock
    private ProductRepository productRepository;
    
    @InjectMocks
    private ProductService productService;
    
    @Test
    void shouldCalculateDiscountForEligibleProduct() {
        Product product = new Product("Test", 150.0);
        
        double discounted = productService.calculateDiscountedPrice(product);
        
        assertEquals(135.0, discounted); // 10% discount
    }
    
    @Test
    void shouldNotAllowNegativePrice() {
        ProductRequest request = new ProductRequest("Test", -10.0);
        
        assertThrows(InvalidProductException.class, () -> {
            productService.createProduct(request);
        });
    }
}
```

## Key Principles

### Single Responsibility
Each service method should implement one clear business use case.

### No Framework Dependencies
Services should not depend on Spring MVC, JAX-RS, or other framework-specific APIs. Use only domain and repository interfaces.

### Testability
All business logic should be testable without starting a web server or database.

### Reusability
Services should be usable from controllers, CLI tools, batch jobs, or any other interface.

## Summary

The service layer is where all business logic lives. It orchestrates repositories and domain objects to implement use cases. Keeping business logic centralized in services ensures consistency, testability, and maintainability. Controllers should only delegate to services, and repositories should only provide data access.