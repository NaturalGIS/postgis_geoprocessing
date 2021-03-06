# -*- coding: utf-8 -*-

"""
***************************************************************************
    closestpoint.py
    ---------------------
    Date                 : August 2019
    Copyright            : (C) 2019 by Giovanni Manghi
    Email                : giovanni dot manghi at naturalgis dot pt
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

__author__ = 'Alexander Bruy and Giovanni Manghi'
__date__ = 'August 2019'
__copyright__ = '(C) 2019, Giovanni Manghi'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os

from qgis.PyQt.QtGui import QIcon

from qgis.core import (QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterField,
                       QgsProcessingParameterString,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterVectorLayer,
                       QgsDataSourceUri
                      )
from processing.algs.gdal.GdalUtils import GdalUtils

pluginPath = os.path.dirname(__file__)


class closestpoint(QgsProcessingAlgorithm):

    INPUT_LAYER_A = 'INPUT_LAYER_A'
    INPUT_LAYER_B = 'INPUT_LAYER_B'
    FIELD_A = 'FIELD_A'
    FIELD_B = 'FIELD_B'
    FIELDS = 'FIELDS'
    MULTI = 'MULTI'
    TABLE = 'TABLE'
    SCHEMA = 'SCHEMA'
    OPTIONS = 'OPTIONS'

    def __init__(self):
        super().__init__()

    def createInstance(self):
        return type(self)()

    def icon(self):
        return QIcon(os.path.join(pluginPath, 'icons', 'postgis.png'))

    def name(self):
        return 'closestpointwithdistance'

    def displayName(self):
        return 'Closest point (with distance)'

    def group(self):
        return 'Vector geoprocessing'

    def groupId(self):
        return 'vectorgeoprocessing'

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT_LAYER_A,
                                                    '"FROM" layer',
                                                    [QgsProcessing.TypeVectorAnyGeometry]))
        self.addParameter(QgsProcessingParameterField(self.FIELD_A,
                                                      '"FROM" layer ID',
                                                      None,
                                                      self.INPUT_LAYER_A))
        self.addParameter(QgsProcessingParameterField(self.FIELDS,
                                                      'Attributes to keep',
                                                      None,
                                                      self.INPUT_LAYER_A,
                                                      allowMultiple=True))
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT_LAYER_B,
                                                            '"TO" layer',
                                                            [QgsProcessing.TypeVectorAnyGeometry]))
        self.addParameter(QgsProcessingParameterField(self.FIELD_B,
                                                      '"TO" layer layer ID',
                                                      None,
                                                      self.INPUT_LAYER_B))
        self.addParameter(QgsProcessingParameterBoolean(self.MULTI,
                                                        'Consider "TO" layer as one unique feature',
                                                        True))
        self.addParameter(QgsProcessingParameterString(self.SCHEMA,
                                                       'Output schema',
                                                       'public'))
        self.addParameter(QgsProcessingParameterString(self.TABLE,
                                                       'Output table name',
                                                       'closest_point'))
        self.addParameter(QgsProcessingParameterString(self.OPTIONS,
                                                       'Additional creation options (see ogr2ogr manual)',
                                                       '',
                                                       optional=True))

    def processAlgorithm(self, parameters, context, feedback):
        inLayerA = self.parameterAsVectorLayer(parameters, self.INPUT_LAYER_A, context)
        ogrLayerA = GdalUtils.ogrConnectionStringFromLayer(inLayerA)
        layernameA = GdalUtils.ogrLayerName(inLayerA.dataProvider().dataSourceUri())

        inLayerB = self.parameterAsVectorLayer(parameters, self.INPUT_LAYER_B, context)
        ogrLayerB = GdalUtils.ogrConnectionStringFromLayer(inLayerB)
        layernameB = GdalUtils.ogrLayerName(inLayerB.dataProvider().dataSourceUri())

        fieldA = self.parameterAsString(parameters, self.FIELD_A, context)
        fieldB = self.parameterAsString(parameters, self.FIELD_B, context)

        uri = QgsDataSourceUri(inLayerA.source())
        geomColumnA = uri.geometryColumn()
        uri = QgsDataSourceUri(inLayerB.source())
        geomColumnB = uri.geometryColumn()

        sridA = inLayerA.crs().postgisSrid()

        fields = self.parameterAsFields(parameters, self.FIELDS, context)

        multi = self.parameterAsBool(parameters, self.MULTI, context)
        schema = self.parameterAsString(parameters, self.SCHEMA, context)
        table = self.parameterAsString(parameters, self.TABLE, context)
        options = self.parameterAsString(parameters, self.OPTIONS, context)

        if len(fields) > 0:
           fieldstring = ','.join(["g1.{}".format(f) for f in fields])
           fieldstring = ", " + fieldstring
        else:
           fieldstring = ""

        if multi:
           sqlstring = "-sql \"WITH temp_table AS (SELECT ST_Union(" + geomColumnB + ") AS geom FROM " + layernameB + ") SELECT (ST_ClosestPoint(g2.geom, g1." + geomColumnA + "))::geometry(POINT," + str(sridA) + ") AS geom, ST_Distance(g1." + geomColumnA + ",g2.geom) AS distance, g1." + fieldA + " AS id_from" + fieldstring +  " FROM " + layernameA + " AS g1, temp_table AS g2\" -nln " + schema + "." + table + " -lco FID=gid -lco GEOMETRY_NAME=geom -nlt POINT --config PG_USE_COPY YES -a_srs EPSG:" + str(sridA) + ""
        else:
           sqlstring = "-sql \"SELECT (ST_ClosestPoint(g2." + geomColumnB + ",g1." + geomColumnA + "))::geometry(Point," + str(sridA) + ") AS geom, ST_Distance(g1." + geomColumnA + ",g2." + geomColumnB + ") AS distance, g1." + fieldA + " AS id_from" + fieldstring + ", g2." + fieldB + " AS id_to FROM " + layernameA + " AS g1, " + layernameB + " AS g2\" -nln " + schema + "." + table + " -lco FID=gid -lco GEOMETRY_NAME=geom -nlt POINT --config PG_USE_COPY YES"

        arguments = []
        arguments.append('-f')
        arguments.append('PostgreSQL')
        arguments.append(ogrLayerA)
        arguments.append(ogrLayerA)
        arguments.append(sqlstring)
        arguments.append('-overwrite')

        if len(options) > 0:
            arguments.append(options)

        commands = ['ogr2ogr', GdalUtils.escapeAndJoin(arguments)]
        GdalUtils.runGdal(commands, feedback)

        return {}
