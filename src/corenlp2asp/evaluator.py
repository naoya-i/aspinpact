
class evaluator_t:
    def __init__(self, doc):
        self.doc = doc

        
    def _xfNumber(self, tk):
        return self.doc.tokens[tk]

        
    def _xfGender(self, tk):
        return "A"

        
    def _xfSenti(self, tk):
        return "A"

        
    def _xfSlotSenti(self, tk, slot):
        return "A"
        
        
