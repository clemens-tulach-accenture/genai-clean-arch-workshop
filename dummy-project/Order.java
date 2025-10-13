package com.example.leakydemo;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;

@Entity
public class Order {

    @Id
    @GeneratedValue
    private Long id;

    private double total;

    // Business logic leakage: Discount calculation in entity getter
    public double getDiscountedTotal() {
        if (total > 100) {
            return total * 0.9; // 10% discount for large orders
        }
        return total;
    }

    // Getters and setters
    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public double getTotal() {
        return total;
    }

    public void setTotal(double total) {
        this.total = total;
    }
}