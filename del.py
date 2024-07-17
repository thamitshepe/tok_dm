from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from lead_gen_gram import User, Base  # Import your ORM classes

# Set up database engine
engine = create_engine('sqlite:///instagram.db')
Base.metadata.bind = engine

# Create a session
Session = sessionmaker(bind=engine)
session = Session()

# Delete all usernames from the users table
session.query(User).delete()

# Commit the transaction
session.commit()

# Close the session
session.close()
