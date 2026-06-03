-- Create function that sends NOTIFY when task status changes
CREATE OR REPLACE FUNCTION notify_task_status_change()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'UPDATE' AND NEW.status != OLD.status) OR (TG_OP = 'INSERT') THEN
        PERFORM pg_notify(
            'task_status_change',
            json_build_object(
                'task_id', NEW.id,
                'status', NEW.status,
                'operation', TG_OP
            )::text
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger that calls the notify function on INSERT or UPDATE
DROP TRIGGER IF EXISTS tasks_notify_trigger ON tasks;
CREATE TRIGGER tasks_notify_trigger
AFTER INSERT OR UPDATE ON tasks
FOR EACH ROW
EXECUTE FUNCTION notify_task_status_change();
