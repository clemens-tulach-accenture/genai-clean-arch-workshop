package com.example.leakydemo;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import java.util.List;

@RestController
public class OrderController {

    @Autowired
    private OrderRepository orderRepository;

    // Business logic leakage: Controller handling business rules like approval checks
    @GetMapping("/orders/eligible")
    public List<Order> getEligibleOrders() {
        List<Order> eligibleOrders = orderRepository.findEligibleForDiscount();
        // Additional leakage: Business decision in controller
        for (Order order : eligibleOrders) {
            if (order.getTotal() > 500) {
                // Approve high-value orders directly here, instead of in domain service
                order.setTotal(order.getTotal() * 0.95); // Extra 5% for VIP
            }
        }
        return eligibleOrders;
    }
}