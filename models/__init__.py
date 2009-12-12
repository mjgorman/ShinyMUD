SAVE_MODELS = [ 'shinymud.models.area.Area',
                'shinymud.models.user.User']

class ShinyModel(object):
    
    # A dictionary of names of attributes to be saved, and their default values.
    # in the format {attribute_name: [defaultvalue, type]}
    save_attrs = {}
    # a list of names of attributes that allow us to reference a unique instance of this model.
    UNIQUE = []
    
    def __init__(self, **args):
        """Initialize saveable data, and other attributes by keyword args.
        
        if you overwrite this, you should either 
        1) call the super class' init function
        2) understand that you are in charge of handling ALL of the initializing, and plan appropriately.
        """
        self.__changed = True # this instances has been modified, or has not been saved.
        for key, val in args.items():
            setattr(self, key, val)
        for attr in [_ for _ in self.save_attrs if _ not in args]:
            setattr(self, _, self.save_attrs[_][0])
    
    def __setattr__(self, key, val):
        if key in self.save_attrs:
            self.__changed = True
        self.__dict__[key] = val
    
    def __ischanged(self):
        try:
            return self.__changed
        except:
            return False
    
    def __exists(self):
        try:
            return bool(self.__dbid)
        except:
            return False
        
    def __get_table_name(self):
        return getattr(self, 'table_name', self.__class__.__name__.lower())
    
    def load(self, conn, **criteria):
        # Try to load from cache.
        # if not in cache, load from db
        cursor = conn.cursor()
        table_name = self.__get_table_name()
        cols = self.save_attrs.keys()
        if not criteria:
            if not self.__exists:
                return 
            criteria = {'dbid':self.__dbid}
        where_clause = " AND ".join([key + "='" + val + "'" for key,val in criteria.items()])
        cursor.execute('SELECT * FROM ? WHERE ? LIMIT 1', (",".join(cols), table_name, where_clause))
        row = cursor.fetchone()
        if row and len(row) == len(cols):
            for i in range(len(row)):
                setattr(self, cols[i], self.save_attrs[cols[i]][1](row[i]))
            self.__changed = False
            self.__exists = True
        # if loaded from db, add to cache
    
    def save(self, conn):
        if self.__ischanged():
            cols = self.save_attrs.keys()
            cursor = conn.cursor()
            table_name = self.__get_table_name()
            if self.__exists:
                # update
                set_values = []
                for key in cols:
                    set_values.append(key + "='" + str(getattr(self, key)) + "'")
                where_clause = "dbid=" + str(self.__dbid)
                cursor.execute("UPDATE ? SET ? WHERE ?", 
                                (table_name, ", ".join(set_values), where_clause))
            else:
                # insert
                data = []
                for key in cols:
                    data.append(str(getattr(self, key)))
                cursor.execute("INSERT INTO ? (?) VALUES (?)", 
                                (table_name, ",".join(self.cols), ','.join(["'" + str(_) + "'" for _ in data])))
                self.__dbid = cursor.lastrowid
    
    def delete(self, conn):
        if self.id:
            cursor = conn.cursor()
            table_name = self.__get_table_name()
            cursor.execute('DELETE FROM ? WHERE id=?', (table_name, self.id))
    
