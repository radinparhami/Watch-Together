from sqlalchemy import create_engine, MetaData, Table, insert, delete, select, update


class Data_Base:

    def __init__(self, data_base_name): self.engine, self.meta = create_engine(data_base_name), MetaData()

    def create(self, data, execute=True):
        return data, (self.engine.execute(data) if execute else None), self.meta.create_all(self.engine)

    def update(self, table, where_clause, **values): self.create(update(table).where(where_clause).values(values))

    def table(self, table_name, *columns): return self.create(Table(table_name, self.meta, *columns), False)[0]

    def select(self, table_name, where_clause=None): return list(self.create(table_name.select(where_clause))[1])

    def delete(self, table, where_clause): self.create(delete(table).where(where_clause))

    def insert(self, table, **values): self.create(insert(table).values(values))
