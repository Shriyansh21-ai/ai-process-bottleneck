from sklearn.metrics import accuracy_score, precision_score

def evaluate_model(model, X, y):
    preds = model.predict(X)
    return {
        "accuracy": accuracy_score(y, preds),
        "precision": precision_score(y, preds)
    }
