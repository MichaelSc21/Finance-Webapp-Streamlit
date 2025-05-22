import streamlit as st
import json


def show_state_main():
    for key, value in st.session_state.items():
        if key == "categories":
            value = json.dumps(value, indent=4, sort_keys=True)
            st.write(f"{key}:")
            st.json(value, expanded=False)
        else:
            st.write(f"{key}: {value}")


if __name__ == '__main__':
    show_state_main()