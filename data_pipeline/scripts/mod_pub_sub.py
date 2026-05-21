from airflow.providers.google.cloud.sensors.pubsub import PubSubPullSensor
from airflow.providers.google.cloud.hooks.pubsub import PubSubHook
from airflow.providers.google.cloud.hooks.gcs import GCSHook

BUCKET_NAME = "us-east1-mlops-dev-8ad13d78-bucket"
SEEN_PATH = "resumes/seen_directories.txt"


class PubSubFinalizeSensor(PubSubPullSensor):
    """
    A sensor that only returns True when it sees at least one OBJECT_FINALIZE
    event.  All messages (finalize or not) are ack’ed so you never re‐see them.
    The finalize messages are pushed to XCom under key='messages'.
    """

    def poke(self, context):
        from google.cloud.exceptions import NotFound
        # Pull up to max_messages (list of SubscriberResponse)
        hook = PubSubHook(
            gcp_conn_id=self.gcp_conn_id,
            impersonation_chain=self.impersonation_chain,
            # enable_message_ordering=self.enable_message_ordering
        )
        response = hook.pull(
            subscription=self.subscription,
            max_messages=self.max_messages,
            return_immediately=True,
            project_id=self.project_id
        )
        if hasattr(response, "received_messages"):
            recs = response.received_messages or []
        else:
            # sometimes PullResponse is itself a RepeatedComposite (list‑like)
            recs = list(response) if response else []
        print("Length of recs: ", len(recs))
        if not recs:
            return False

        # Partition into finalize vs everything else
        finalize_msgs = []
        ack_ids = []
        gcs_hook = GCSHook(gcp_conn_id=self.gcp_conn_id)
        client = gcs_hook.get_conn()
        bucket = client.get_bucket(BUCKET_NAME)
        # 2) point at the "seen" file
        blob = bucket.blob(SEEN_PATH)
        # 3) try to download & parse it, or start empty if it doesn't exist
        try:
            text = blob.download_as_text()  # returns str
            seen = [line.strip() for line in text.splitlines() if line.strip()]
        except NotFound:
            seen = []
        seen.append("seen_directories.txt")
        for rec in recs:
            ack_id = getattr(rec, "ack_id", None)
            msg = getattr(rec, "message", rec)

            if ack_id:
                ack_ids.append(ack_id)

            print(msg.attributes.get("eventType"))
            if getattr(msg, "attributes", {}).get("eventType") == "OBJECT_FINALIZE":
                subdir = msg.attributes['objectId'].split('/')[1]
                if subdir in seen or subdir in ["test_embeddings_20250420_104122.npz", "metadata_20250420_104122.json"]:
                    continue
                # log.info(f"New subdirectory: {subdir}")
                seen.append(subdir)
                blob.upload_from_string(
                    "\n".join(seen),
                    content_type="text/plain"
                )
                finalize_msgs.append(msg)

        events = []
        for msg in finalize_msgs:
            # decode bytes → str
            raw = msg.data.decode('utf-8') if isinstance(msg.data, (bytes, bytearray)) else msg.data
            events.append({
                "data": raw,
                "attributes": dict(msg.attributes or {}),
            })

        # Ack *all* so you never see them again
        if ack_ids:
            hook.acknowledge(
                subscription=self.subscription,
                project_id=self.project_id,
                ack_ids=ack_ids,
            )

        if finalize_msgs:
            # push only the finalize messages for downstream
            context['ti'].xcom_push(key="events", value=events)
            return True

        # no finalize events yet → keep poking
        return False