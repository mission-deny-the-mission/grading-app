#!/bin/bash
echo "Stopping PostgreSQL..."
pg_ctl -D .postgres_data stop
echo "Stopping Redis..."
pkill redis-server
echo "Services stopped."
