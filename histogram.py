import psycopg2
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import pandas as pd
import seaborn as sns

DB_CONFIG = {
    "host": "192.168.4.32",
    "port": 5432,
    "dbname": "postgres",
    "user": "postgres",
    "password":"5452",
}

QUERY = """
SELECT steam_id, SUM(historical_low_price) AS account_value
FROM user_library JOIN games USING(app_id)
GROUP BY steam_id
HAVING SUM(historical_low_price) < 4000;
"""

with psycopg2.connect(**DB_CONFIG) as con:
    cur = con.cursor()
    cur.execute(QUERY)
    data = {*cur.fetchall()}

df = pd.DataFrame(data=data, columns=["steam_id", "account_value"])

sns.histplot(data=df, x="account_value", bins=[i*100 for i in range(40)])
plt.title("Histogram distribuce útrat uživatelů")
plt.xlabel("Celková cena účtu v EUR")
plt.ylabel("Počet")
plt.xticks(ticks=[i*500 for i in range(9)])
plt.show()