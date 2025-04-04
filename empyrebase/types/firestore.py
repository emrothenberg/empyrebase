class Document(dict):
    exists: bool
    def __init__(self, data, exists=True):
        super().__init__(data)
        self.exists = exists
        
    def to_dict(self):
        return dict(self)
