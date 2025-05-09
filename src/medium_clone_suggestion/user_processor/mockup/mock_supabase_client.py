# This file would normally contain the actual Supabase client implementation
# For testing, we're providing a mock version

class SupabaseClient:
    """Mock implementation of the Supabase client for local testing"""
    
    def __init__(self):
        """Initialize the mock client"""
        pass
        
    def get_client(self):
        """Return a mock client object that can be used in place of the real one"""
        return MockClient()
        
class MockClient:
    """Mock Supabase client implementation"""
    
    def table(self, table_name):
        """Mock table method"""
        return MockTable(table_name)
    
    def rpc(self, function_name, params=None):
        """Mock RPC method"""
        return MockRPCBuilder(function_name, params)
        
class MockTable:
    """Mock Supabase table"""
    
    def __init__(self, table_name):
        self.table_name = table_name
        
    def select(self, columns):
        """Mock select method"""
        return self
        
    def in_(self, column, values):
        """Mock in_ method"""
        return self
        
    def execute(self):
        """Mock execute method"""
        # This would normally return data from Supabase
        # For testing, it returns an empty result
        return MockResult([])
        
    def upsert(self, data):
        """Mock upsert method"""
        return self
        
class MockRPCBuilder:
    """Mock RPC builder"""
    
    def __init__(self, function_name, params=None):
        self.function_name = function_name
        self.params = params or {}
        
    def execute(self):
        """Mock execute method"""
        # This would normally call an RPC function in Supabase
        # For testing, it returns an empty result
        return MockResult([])
        
class MockResult:
    """Mock result from Supabase operations"""
    
    def __init__(self, data):
        self.data = data