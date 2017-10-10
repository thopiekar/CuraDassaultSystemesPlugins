project(SolidWorksPlugin NONE)
cmake_minimum_required(VERSION 2.8.12)

install(FILES
    __init__.py
    CommonComReader.py
    SolidWorksConstants.py
    SolidWorksReader.py
    LICENSE
    DESTINATION lib/cura/plugins/SolidWorksPlugin
)