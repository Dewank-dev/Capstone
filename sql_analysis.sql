-- Local Food Wastage Management System
-- SQL Analysis Queries for SQLite
-- Tables used: providers, receivers, food_listings, claims

-- 1. Providers by city
SELECT
    City,
    COUNT(*) AS provider_count
FROM providers
GROUP BY City
ORDER BY provider_count DESC, City;

-- 2. Receivers by city
SELECT
    City,
    COUNT(*) AS receiver_count
FROM receivers
GROUP BY City
ORDER BY receiver_count DESC, City;

-- 3. Most contributing provider by total donated quantity
SELECT
    p.Provider_ID,
    p.ProviderName,
    p.City,
    SUM(f.Quantity) AS total_donated_quantity
FROM providers p
JOIN food_listings f
    ON p.Provider_ID = f.Provider_ID
GROUP BY p.Provider_ID, p.ProviderName, p.City
ORDER BY total_donated_quantity DESC
LIMIT 1;

-- 4. Most claimed food
SELECT
    f.Food_ID,
    f.Food_Name,
    COUNT(c.Claim_ID) AS claim_count
FROM food_listings f
JOIN claims c
    ON f.Food_ID = c.Food_ID
GROUP BY f.Food_ID, f.Food_Name
ORDER BY claim_count DESC, f.Food_Name
LIMIT 1;

-- 5. Total food quantity available/donated
SELECT
    SUM(Quantity) AS total_food_quantity
FROM food_listings;

-- 6. Top city by food listings
SELECT
    City,
    COUNT(*) AS listing_count
FROM food_listings
GROUP BY City
ORDER BY listing_count DESC, City
LIMIT 1;

-- 7. Most common food type
SELECT
    Food_Type,
    COUNT(*) AS food_type_count
FROM food_listings
GROUP BY Food_Type
ORDER BY food_type_count DESC, Food_Type
LIMIT 1;

-- 8. Claims per food item
SELECT
    f.Food_ID,
    f.Food_Name,
    COUNT(c.Claim_ID) AS claim_count
FROM food_listings f
LEFT JOIN claims c
    ON f.Food_ID = c.Food_ID
GROUP BY f.Food_ID, f.Food_Name
ORDER BY claim_count DESC, f.Food_Name;

-- 9. Provider with most successful claims
SELECT
    p.Provider_ID,
    p.ProviderName,
    COUNT(c.Claim_ID) AS successful_claims
FROM providers p
JOIN food_listings f
    ON p.Provider_ID = f.Provider_ID
JOIN claims c
    ON f.Food_ID = c.Food_ID
WHERE LOWER(c.Status) IN ('completed', 'complete', 'done', 'claimed')
GROUP BY p.Provider_ID, p.ProviderName
ORDER BY successful_claims DESC, p.ProviderName
LIMIT 1;

-- 10. Claim status percentage
SELECT
    Status,
    COUNT(*) AS claim_count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM claims), 2) AS status_percentage
FROM claims
GROUP BY Status
ORDER BY status_percentage DESC;

-- 11. Average quantity claimed per receiver
SELECT
    r.Receiver_ID,
    r.Name AS receiver_name,
    ROUND(AVG(f.Quantity), 2) AS average_quantity_claimed
FROM receivers r
JOIN claims c
    ON r.Receiver_ID = c.Receiver_ID
JOIN food_listings f
    ON c.Food_ID = f.Food_ID
GROUP BY r.Receiver_ID, r.Name
ORDER BY average_quantity_claimed DESC;

-- 12. Most claimed meal type
SELECT
    f.Meal_Type,
    COUNT(c.Claim_ID) AS claim_count
FROM food_listings f
JOIN claims c
    ON f.Food_ID = c.Food_ID
GROUP BY f.Meal_Type
ORDER BY claim_count DESC, f.Meal_Type
LIMIT 1;

-- 13. Total donated quantity by provider
SELECT
    p.Provider_ID,
    p.ProviderName,
    SUM(f.Quantity) AS total_donated_quantity
FROM providers p
LEFT JOIN food_listings f
    ON p.Provider_ID = f.Provider_ID
GROUP BY p.Provider_ID, p.ProviderName
ORDER BY total_donated_quantity DESC;

-- 14. Food availability: city with the most food quantity
SELECT
    City,
    SUM(Quantity) AS total_available_quantity
FROM food_listings
GROUP BY City
ORDER BY total_available_quantity DESC, City
LIMIT 1;

-- 15. Food waste: meal type with the highest available quantity
SELECT
    Meal_Type,
    SUM(Quantity) AS total_quantity
FROM food_listings
GROUP BY Meal_Type
ORDER BY total_quantity DESC, Meal_Type
LIMIT 1;

-- 16. Receiver analysis: receiver who claims the most food quantity
SELECT
    r.Receiver_ID,
    r.Name AS receiver_name,
    SUM(f.Quantity) AS total_claimed_quantity
FROM receivers r
JOIN claims c
    ON r.Receiver_ID = c.Receiver_ID
JOIN food_listings f
    ON c.Food_ID = f.Food_ID
GROUP BY r.Receiver_ID, r.Name
ORDER BY total_claimed_quantity DESC
LIMIT 1;

-- 17. Claims analysis: completed claim percentage
SELECT
    COUNT(*) AS total_claims,
    SUM(CASE WHEN LOWER(Status) IN ('completed', 'complete', 'done', 'claimed') THEN 1 ELSE 0 END) AS completed_claims,
    ROUND(
        100.0 * SUM(CASE WHEN LOWER(Status) IN ('completed', 'complete', 'done', 'claimed') THEN 1 ELSE 0 END)
        / COUNT(*),
        2
    ) AS completed_percentage
FROM claims;

-- 18. Demand analysis: city with highest food demand by number of claims
SELECT
    r.City,
    COUNT(c.Claim_ID) AS demand_claim_count
FROM receivers r
JOIN claims c
    ON r.Receiver_ID = c.Receiver_ID
GROUP BY r.City
ORDER BY demand_claim_count DESC, r.City
LIMIT 1;

-- 19. Demand analysis: city with highest claimed quantity
SELECT
    r.City,
    SUM(f.Quantity) AS demanded_quantity
FROM receivers r
JOIN claims c
    ON r.Receiver_ID = c.Receiver_ID
JOIN food_listings f
    ON c.Food_ID = f.Food_ID
GROUP BY r.City
ORDER BY demanded_quantity DESC, r.City
LIMIT 1;

-- 20. Expiring food listings for automated notification recommendation
SELECT
    Food_ID,
    Food_Name,
    City,
    Quantity,
    Expiry_Date
FROM food_listings
WHERE DATE(Expiry_Date) <= DATE('now', '+3 day')
ORDER BY DATE(Expiry_Date), City, Food_Name;

-- 21. Cities with high food availability but low claims
SELECT
    f.City,
    SUM(f.Quantity) AS available_quantity,
    COUNT(c.Claim_ID) AS claim_count
FROM food_listings f
LEFT JOIN claims c
    ON f.Food_ID = c.Food_ID
GROUP BY f.City
ORDER BY available_quantity DESC, claim_count ASC;

-- 22. Provider recognition list: top providers by quantity and successful claims
SELECT
    p.Provider_ID,
    p.ProviderName,
    p.City,
    SUM(f.Quantity) AS total_donated_quantity,
    SUM(CASE WHEN LOWER(c.Status) IN ('completed', 'complete', 'done', 'claimed') THEN 1 ELSE 0 END) AS successful_claims
FROM providers p
LEFT JOIN food_listings f
    ON p.Provider_ID = f.Provider_ID
LEFT JOIN claims c
    ON f.Food_ID = c.Food_ID
GROUP BY p.Provider_ID, p.ProviderName, p.City
ORDER BY total_donated_quantity DESC, successful_claims DESC;

