import matplotlib.pyplot as plt
import pandas as pd
import os

def plot_feature_importance(model, vectorizer, top_k=15, filename="feature_importance.png"):
    """
    Simple function to plot feature importance and save to ../report/_static
    
    Parameters:
    -----------
    model : trained sklearn model (tree-based or logistic regression)
    vectorizer : fitted vectorizer (CountVectorizer or TfidfVectorizer)
    top_k : int, number of top features to show
    filename : str, output filename
    """
    # Get feature importance based on model type
    if hasattr(model, 'feature_importances_'):
        # Tree-based models (RandomForest, XGBoost, etc.)
        importance = model.feature_importances_
    elif hasattr(model, 'coef_'):
        # Linear models (LogisticRegression, SVM, etc.)
        importance = abs(model.coef_[0])  # Use absolute values of coefficients
    else:
        raise ValueError("Model must have either 'feature_importances_' or 'coef_' attribute")
    
    features = vectorizer.get_feature_names_out()
    
    # Create DataFrame and get top features
    df = pd.DataFrame({'feature': features, 'importance': importance})
    top_features = df.nlargest(top_k, 'importance')
    
    # Create plot
    plt.figure(figsize=(10, 6))
    plt.barh(range(len(top_features)), top_features['importance'])
    plt.yticks(range(len(top_features)), top_features['feature'])
    plt.xlabel('Feature Importance')
    plt.title(f'Top {top_k} Most Important Features')
    plt.gca().invert_yaxis()
    plt.tight_layout()
    
    # Save plot
    os.makedirs("../report/_static", exist_ok=True)
    plt.savefig(f"../report/_static/{filename}", dpi=300, bbox_inches='tight')
    plt.show()
    
    print(f"Plot saved to: ../report/_static/{filename}")