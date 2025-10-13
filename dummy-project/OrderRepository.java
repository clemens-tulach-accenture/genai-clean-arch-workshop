package com.example.leakydemo;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface OrderRepository extends JpaRepository<Order, Long> {

    // Business logic leakage: Custom query mixing data access with business rule (eligibility check)
    @Query("SELECT o FROM Order o WHERE o.total > 0")
    List<Order> findAllOrders();

    // Leakage example: Method with inline business logic
    default List<Order> findEligibleForDiscount() {
        List<Order> orders = findAllOrders();
        // Business rule in repository: Filter and calculate discount here instead of service
        return orders.stream()
                .filter(order -> order.getTotal() > 100)
                .peek(order -> order.setTotal(order.getDiscountedTotal())) // Mutating entity with business logic
                .toList();
    }
}