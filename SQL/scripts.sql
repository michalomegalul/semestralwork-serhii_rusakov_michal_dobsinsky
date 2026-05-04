SELECT steam_id, account_created_at,
CASE
    WHEN account_created_at BETWEEN '2016-01-01' AND '2020-03-01' THEN 'Pre-COVID (2018-2020)'
    WHEN account_created_at BETWEEN '2020-03-01' AND '2021-12-31' THEN 'COVID period'
    ELSE 'Post-COVID (2022+)'
END AS time_category
FROM (
    SELECT *
    FROM users
    WHERE account_created_at > '2016-01-01');


select steam_id, app_id, title, historical_low_price
from user_library JOIN games USING(app_id)
LIMIT (10);

select steam_id, SUM(historical_low_price) AS account_value
from user_library JOIN games USING(app_id)
GROUP BY steam_id;