# Demo scenario

This demo verifies the end-to-end notification flow.

## Steps

Start services:

```bash
cp .env.sample .env
make up
```
Run demo:

```bash
make demo
```
### What happens

- A notification template is created
- A notification event is published
- The event is written to Kafka (outbox pattern)
- Worker consumes the event and sends an email
- Delivery result is persisted

### Verification
Open Mailpit UI:

http://localhost:${MAILPIT_UI_PORT}

You should see the delivered email message.

---