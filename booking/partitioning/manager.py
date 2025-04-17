from dateutil.relativedelta import relativedelta
from psqlextra.partitioning import (
    PostgresPartitioningManager,
    PostgresCurrentTimePartitioningStrategy,
    PostgresTimePartitionSize,
)
from psqlextra.partitioning.config import PostgresPartitioningConfig

from booking.models import Booking

# модель Booking должна быть импортируема!
manager = PostgresPartitioningManager([
    PostgresPartitioningConfig(
        model=Booking,
        strategy=PostgresCurrentTimePartitioningStrategy(
            size=PostgresTimePartitionSize(months=1),
            count=3,
            max_age=relativedelta(months=6),
        ),
    ),
])
