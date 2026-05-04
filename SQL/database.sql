SELECT steam_id, achievement_timestamp,
CASE
    WHEN achievement_timestamp BETWEEN '2016-01-01' AND '2020-03-01' THEN 'Pre-COVID (2016-2020)'
    WHEN achievement_timestamp BETWEEN '2020-03-01' AND '2021-12-31' THEN 'COVID period (2020-2022)'
    ELSE 'Post-COVID (2022+)'
END AS time_category
FROM (
    SELECT *
    FROM activity_timeline
    WHERE achievement_timestamp >= '2016-01-01')
GROUP BY steam_id, time_category;

SELECT date_trunc('day', achievement_timestamp + INTERVAL '12 hours'),
CASE
    WHEN achievement_timestamp BETWEEN '2016-01-01' AND '2020-03-01' THEN 'Pre-COVID (2016-2020)'
    WHEN achievement_timestamp BETWEEN '2020-03-01' AND '2021-12-31' THEN 'COVID period (2020-2022)'
    ELSE 'Post-COVID (2022+)'
END AS time_category, COUNT(date_trunc('day', achievement_timestamp + INTERVAL '12 hours'))
FROM (
    SELECT *
    FROM activity_timeline
    WHERE achievement_timestamp >= '2016-01-01')
GROUP BY date_trunc('day', achievement_timestamp + INTERVAL '12 hours'), time_category
ORDER BY COUNT(date_trunc('day', achievement_timestamp + INTERVAL '12 hours')) DESC;

SELECT *
FROM activity_timeline
LIMIT(10);

SELECT date_trunc('day', achievement_timestamp + INTERVAL '12 hours') AS rounded_date
FROM activity_timeline
LIMIT(10);

SELECT date_trunc('day', account_created_at + INTERVAL '12 hours'),
CASE
    WHEN account_created_at BETWEEN '2016-01-01' AND '2020-03-01' THEN 'Pre-COVID (2016-2020)'
    WHEN account_created_at BETWEEN '2020-03-01' AND '2021-12-31' THEN 'COVID period (2020-2022)'
    ELSE 'Post-COVID (2022+)'
END AS time_category, COUNT(date_trunc('day', account_created_at + INTERVAL '12 hours'))
FROM (
    SELECT *
    FROM users
    WHERE account_created_at >= '2016-01-01')
GROUP BY date_trunc('day', account_created_at + INTERVAL '12 hours'), time_category
ORDER BY COUNT(date_trunc('day', account_created_at + INTERVAL '12 hours')) DESC;

SELECT steam_id, account_created_at,
CASE
    WHEN account_created_at BETWEEN '2016-01-01' AND '2020-03-01' THEN 'Pre-COVID (2016-2020)'
    WHEN account_created_at BETWEEN '2020-03-01' AND '2021-12-31' THEN 'COVID period (2020-2022)'
    ELSE 'Post-COVID (2022+)'
END AS time_category
FROM (
    SELECT *
    FROM users
    WHERE account_created_at >= '2016-01-01');