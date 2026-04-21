import asyncio
import logging
import sys
from datetime import datetime

from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic

from body_composition import calculate_body_composition
from database import init_db, save_measurement
from parsing import parse_body_composition_message
from user_config import AGE, HEIGHT_CM, SEX

BODY_COMPOSITION_MEASUREMENT_UUID = "00002a9c-0000-1000-8000-00805f9b34fb"

logger = logging.getLogger(__name__)

# Track last stable measurement to avoid duplicate saves
_last_saved_weight: float | None = None


async def find_miscale_device():
    logger.info("🔍 Scanning for Mi Scale (MIBFS)...")
    return await BleakScanner().find_device_by_name("MIBFS")


def notification_handler(characteristic: BleakGATTCharacteristic, data: bytearray):
    global _last_saved_weight
    message = parse_body_composition_message(data)
    m = message.measurement
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not message.stabilized or m.impedance == 0:
        # Overwrite same line while waiting — no spam
        sys.stdout.write(
            f"\r  ⏳ Stabilizing...  ⚖️  {m.weight:.2f} kg   "
        )
        sys.stdout.flush()
        return

    if m.impedance >= 3000:
        sys.stdout.write(
            f"\r  ⚠️  Impedance too high ({m.impedance} ohm) — both feet on scale?   "
        )
        sys.stdout.flush()
        return

    # --- Valid stable measurement ---
    comp = calculate_body_composition(m.weight, m.impedance, HEIGHT_CM, AGE, SEX)

    # Avoid saving duplicate if weight didn't change
    if _last_saved_weight == m.weight:
        return
    _last_saved_weight = m.weight

    print()  # newline after the \r line
    print("\n" + "=" * 50)
    print(f"  🕐 Timestamp    : {now}")
    print(f"  ⚖️  Weight       : {m.weight:.2f} kg  ({m.weight * 2.20462:.2f} lbs)")
    print(f"  ⚡ Impedance    : {m.impedance} ohm")
    print(f"  📊 BMI          : {comp.bmi}")
    print(f"  🥩 Body Fat     : {comp.fat_percent} %")
    print(f"  💪 Muscle Mass  : {comp.muscle_mass_kg} kg")
    print(f"  🦴 Bone Mass    : {comp.bone_mass_kg} kg")
    print(f"  💧 Water        : {comp.water_percent} %")
    print(f"  🫀 Visceral Fat : {comp.visceral_fat}")
    print(f"  🔥 BMR          : {comp.bmr_kcal} kcal/day")
    print(f"  🏃 Lean Mass    : {comp.lean_mass_kg} kg")
    print(f"  🥛 Protein      : {comp.protein_percent} %")
    print("=" * 50)

    # Save to SQLite
    save_measurement(
        timestamp=now,
        weight_kg=m.weight,
        impedance=m.impedance,
        bmi=comp.bmi,
        fat_percent=comp.fat_percent,
        muscle_mass_kg=comp.muscle_mass_kg,
        bone_mass_kg=comp.bone_mass_kg,
        water_percent=comp.water_percent,
        visceral_fat=comp.visceral_fat,
        bmr_kcal=comp.bmr_kcal,
        lean_mass_kg=comp.lean_mass_kg,
        protein_percent=comp.protein_percent,
    )
    logger.info("💾 Saved to SQLite database.")

    # Optional: also save to Google Sheets if configured
    try:
        from sheets import append_measurement
        append_measurement(
            timestamp=now,
            weight=m.weight,
            impedance=m.impedance,
            stabilized=True,
            comp=comp,
        )
    except FileNotFoundError:
        pass  # service_account.json not configured — skip silently
    except Exception as e:
        logger.warning(f"Google Sheets not saved: {e}")


async def connect_and_measure():
    global _last_saved_weight
    _last_saved_weight = None
    disconnected_event = asyncio.Event()

    def disconnected_callback(_bleak_client: BleakClient):
        logger.info("\n📴 Scale disconnected.")
        disconnected_event.set()

    device = await find_miscale_device()

    if not device:
        logger.warning("❌ No Mi Scale found. Retrying in 5 seconds...")
        await asyncio.sleep(5)
        return

    logger.info(f"✅ Found device: {device.name} ({device.address})")

    client = BleakClient(device, disconnected_callback=disconnected_callback)

    async with client:
        logger.info("🔗 Connected! Step on the scale...")
        await client.start_notify(BODY_COMPOSITION_MEASUREMENT_UUID, notification_handler)
        await disconnected_event.wait()


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)-15s %(name)-8s %(levelname)s: %(message)s",
    )
    init_db()
    logger.info(f"🚀 Mi Scale starting... (Profile: {HEIGHT_CM}cm, {AGE}y, {SEX})")
    while True:
        try:
            await connect_and_measure()
        except Exception as e:
            logger.error(f"Error: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)
        logger.info("🔄 Restarting scan...")


if __name__ == "__main__":
    asyncio.run(main())
