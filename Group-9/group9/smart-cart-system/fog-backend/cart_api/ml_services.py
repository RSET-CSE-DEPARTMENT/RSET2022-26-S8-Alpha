import logging
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from .models import OrderItem

logger = logging.getLogger(__name__)

class RecommendationEngine:
    _rules = None

    @classmethod
    def load_and_train(cls):
        """
        Loads historical data from OrderItem, pivots it into a one-hot encoded
        DataFrame, and generates association rules using the Apriori algorithm.
        The rules are cached in the class variable `_rules`.
        """
        logger.info("Initializing Recommendation Engine... Fetching data.")
        
        # Fetch historical data using Django ORM
        # We need order_id and product_id to build the baskets
        items = OrderItem.objects.values("order_id", "product_id")
        df = pd.DataFrame(list(items))
        
        if df.empty:
            logger.warning("No historical OrderItem data found. Cannot train RecommendationEngine.")
            cls._rules = pd.DataFrame()
            return

        # Pivot DataFrame to one-hot encoded format
        # Rows = Order ID, Columns = Product ID, Values = 1 or 0
        df["value"] = 1
        basket = df.pivot_table(
            index="order_id", 
            columns="product_id", 
            values="value", 
            fill_value=0
        )
        
        # Convert to boolean for mlxtend apriori
        basket_bool = basket > 0
        
        logger.info(f"Running Apriori on {len(basket_bool)} orders...")
        
        try:
            # Generate frequent itemsets with lower min_support
            frequent_itemsets = apriori(basket_bool, min_support=0.003, use_colnames=True)
            
            if frequent_itemsets.empty:
                logger.warning("Apriori found no frequent itemsets with the given support.")
                cls._rules = pd.DataFrame()
                return
                
            # Generate association rules
            rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=0.1)
            cls._rules = rules
            logger.info(f"Recommendation Engine trained successfully. Generated {len(rules)} rules.")
        except Exception as e:
            logger.error(f"Error during Apriori training: {e}")
            cls._rules = pd.DataFrame()

    @classmethod
    def get_recommendations(cls, current_cart_product_ids, top_n=3):
        """
        Takes a list of product IDs currently in the cart, checks them against 
        the cached rules, and returns the top recommended Product IDs.
        Falls back to most popular items if rules are empty or yield not enough. 
        """
        if cls._rules is None:
            # First-time initialization
            cls.load_and_train()
            
        recommendations = []
        cart_set = frozenset(current_cart_product_ids)

        if cls._rules is not None and not cls._rules.empty and cart_set:
            # Find rules where antecedents are a subset of the current cart
            matching_rules = cls._rules[
                cls._rules["antecedents"].apply(lambda ants: ants.issubset(cart_set))
            ]
            
            if not matching_rules.empty:
                # Sort by confidence
                sorted_rules = matching_rules.sort_values(
                    ["confidence", "lift"], 
                    ascending=[False, False]
                )
                
                # Extract consequents, avoiding items already in the cart
                for consequents in sorted_rules["consequents"]:
                    for item in consequents:
                        if item not in cart_set and item not in recommendations:
                            recommendations.append(item)
                            if len(recommendations) >= top_n:
                                return recommendations

        # Fallback: if we still need recommendations, add globally popular items
        if len(recommendations) < top_n:
            from django.db.models import Count
            popular_items = OrderItem.objects.values("product_id").annotate(
                count=Count("product_id")
            ).order_by("-count")[:top_n + len(cart_set) + len(recommendations)]
            
            for item in popular_items:
                pid = item["product_id"]
                if pid not in cart_set and pid not in recommendations:
                    recommendations.append(pid)
                    if len(recommendations) >= top_n:
                        break

        return recommendations
