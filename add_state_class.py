# add_state_class.py
entities = ['sensor.gas_consumption', 'sensor.water_consumption']

for entity in entities:
    state = hass.states.get(entity)
    if state is not None:
        state_attrs = state.attributes.copy()
        state_attrs['state_class'] = 'total_increasing'
        hass.states.set(entity, state.state, state_attrs)
