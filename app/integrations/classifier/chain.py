from app.integrations.classifier.base import ClassificationContext, ItemClassifier, Prediction


class ClassifierChain:
    """Menjalankan beberapa classifier berurutan; jawaban pertama dipakai."""

    def __init__(self, classifiers: list[ItemClassifier]):
        self.classifiers = classifiers

    def predict_many(self, texts: list[str], ctx: ClassificationContext) -> list[Prediction | None]:
        results: list[Prediction | None] = [None] * len(texts)
        for classifier in self.classifiers:
            pending = [i for i, r in enumerate(results) if r is None]
            if not pending:
                break
            answers = classifier.predict_many([texts[i] for i in pending], ctx)
            for index, answer in zip(pending, answers):
                results[index] = answer
        return results

    def status(self) -> list[dict]:
        return [c.status() for c in self.classifiers]
