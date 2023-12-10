import enum
import os


class zINI:
    def __init__(self):

        self.data = {}

    def __len__(self):
        return len(self.data)
    
    @staticmethod
    def load(path : os.PathLike):
        ini = zINI()
        
        with open(path, "r") as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            if line == "" or line.startswith("#"):
                continue
            
            key, value = line.split("=", 1)
            ini[key] = value
            
        return ini
    
    def save(self, path : os.PathLike):
        with open(path, "w") as f:
            for key, value in self.data.items():
                f.write(f"{key}={value}\n")
                
        

    def __setitem__(self, key, value):
        self.data[key] = value

    def __getitem__(self, key):
        return self.data[key]