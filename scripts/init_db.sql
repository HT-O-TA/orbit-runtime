CREATE USER temporal WITH PASSWORD 'temporal';
CREATE DATABASE temporal OWNER temporal;

CREATE USER orbit WITH PASSWORD 'orbit_password';
CREATE DATABASE orbit_db OWNER orbit;

GRANT ALL PRIVILEGES ON DATABASE temporal TO temporal;
GRANT ALL PRIVILEGES ON DATABASE orbit_db TO orbit;
