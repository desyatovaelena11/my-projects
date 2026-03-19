-- Миграция: создание таблицы записей клиентов
-- Запустить один раз в Supabase → SQL Editor

CREATE TABLE IF NOT EXISTS bookings (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    master_id        UUID NOT NULL REFERENCES masters(id) ON DELETE CASCADE,

    -- Клиент
    client_telegram_id  BIGINT,
    client_name         VARCHAR(256),
    client_username     VARCHAR(64),

    -- Услуга (snapshot на момент записи)
    service_name         VARCHAR(256) NOT NULL,
    service_price        INTEGER NOT NULL,
    service_duration_min INTEGER NOT NULL,

    -- Дата и время
    booking_date  VARCHAR(10) NOT NULL,  -- YYYY-MM-DD
    booking_time  VARCHAR(5)  NOT NULL,  -- HH:MM

    -- Статус
    status      VARCHAR(16) NOT NULL DEFAULT 'pending',  -- pending | confirmed | cancelled

    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Индекс для быстрого поиска записей по мастеру и дате
CREATE INDEX IF NOT EXISTS idx_bookings_master_date
    ON bookings (master_id, booking_date);
