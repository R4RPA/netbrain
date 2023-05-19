async def device_data_processed(event: events.GetDeviceDataProcessed) -> list[Message]:
    cid = event.cid
    messages: list[Message] = []

    # send this to TestRequestOutbox!
    if event.trid:
        try:
            TestRequestOutbox(
                event_type = "",
                trid = event.trid,
                create_time = datetime.now(timezone.utc),
            ).save()
        except Exception as e:
            logger.warning(f"{cid} TRID={event.trid} Attempt to save CampaignRunInitiated Event to TestRequestOutbox encountered Exception {str(e)}", exc_info=True)
            messages.append(event)
        else:
            logger.info(f"{cid} TRID={event.trid} saved CampaignRunInitiated Event to TestRequestOutbox.")

    return messages
